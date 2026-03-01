"""
Foundation Model APIs（OpenAI 互換）を使用した翻訳クライアント

Databricks の Foundation Model APIs に OpenAI クライアントで接続し、
テキストセグメントのバッチ翻訳を行う。
"""

import os
import re
import time
from typing import List, Optional
from openai import OpenAI
from databricks.sdk import WorkspaceClient

from translator.models import TextSegment, TranslationConfig


def create_client() -> Optional[OpenAI]:
    """
    Databricks Foundation Model APIs 用の OpenAI クライアントを作成する

    環境変数 DATABRICKS_HOST と認証情報から自動的にクライアントを構築する。
    ローカル環境で認証情報がない場合は None を返す（デモモード用）。

    認証方法:
    - ローカル環境: 環境変数 DATABRICKS_TOKEN (PAT)
    - Databricks Apps: 環境変数 DATABRICKS_TOKEN (app.yml で設定)
      または DATABRICKS_CLIENT_ID + DATABRICKS_CLIENT_SECRET (OAuth M2M)

    Returns:
        OpenAI クライアントインスタンス、または None（デモモード）
    """
    try:
        # WorkspaceClient を初期化（自動的に環境変数から認証情報を取得）
        w = WorkspaceClient()

        # ホストが設定されているかチェック
        if not w.config.host:
            return None

        # トークンを取得
        # 方法1: 環境変数から直接取得（PAT）
        token = os.environ.get("DATABRICKS_TOKEN")

        # 方法2: WorkspaceClient の Config.authenticate() で OAuth トークンを取得
        # Databricks Apps 環境では DATABRICKS_CLIENT_ID と DATABRICKS_CLIENT_SECRET が設定される
        if not token:
            try:
                # Config.authenticate() は認証ヘッダーの辞書を返す
                # 例: {'Authorization': 'Bearer ...'}
                auth_headers = w.config.authenticate()
                if auth_headers and 'Authorization' in auth_headers:
                    # 'Bearer ' プレフィックスを除去してトークンを取得
                    auth_value = auth_headers['Authorization']
                    if auth_value.startswith('Bearer '):
                        token = auth_value[7:]  # 'Bearer ' を削除
                    else:
                        token = auth_value
            except Exception:
                # OAuth トークン取得に失敗した場合はデモモード
                pass

        if not token:
            # トークンが設定されていない場合はデモモード
            return None

        # Base URL を構築（host は既に https:// を含む場合がある）
        host = w.config.host
        if host.startswith('https://'):
            host = host[8:]  # 'https://' を除去
        elif host.startswith('http://'):
            host = host[7:]   # 'http://' を除去

        # OpenAI クライアントを作成（Databricks Foundation Model APIs用）
        client = OpenAI(
            base_url=f"https://{host}/serving-endpoints",
            api_key=token,
        )
        return client
    except Exception:
        # 認証情報が取得できない場合はデモモード
        return None


def translate_batch(
    client: Optional[OpenAI],
    segments: List[TextSegment],
    config: TranslationConfig,
    max_retries: int = 2,
) -> List[TextSegment]:
    """
    テキストセグメントのリストをバッチ翻訳する

    Args:
        client: OpenAI クライアント（None の場合はデモモード）
        segments: 翻訳するテキストセグメントのリスト
        config: 翻訳設定
        max_retries: 最大リトライ回数（デフォルト: 2）

    Returns:
        翻訳済みテキストが設定されたセグメントのリスト

    Raises:
        Exception: LLM 呼び出しが max_retries 回失敗した場合
    """
    if not segments:
        return segments

    # デモモード（client が None の場合）
    if client is None:
        return _translate_demo_mode(segments)

    # システムプロンプトとユーザープロンプトを構築
    system_prompt = _build_system_prompt(config)
    user_prompt = _build_user_prompt(segments)

    # LLM を呼び出してレスポンスを取得（リトライあり）
    response_text = None
    for attempt in range(max_retries + 1):
        try:
            response_text = _call_llm(client, system_prompt, user_prompt, config)
            break
        except Exception as e:
            if attempt < max_retries:
                # Exponential Backoff
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                raise Exception(f"LLM call failed after {max_retries + 1} attempts: {e}")

    # レスポンスをパースして翻訳テキストを抽出
    translations = _parse_response(response_text, len(segments))

    # セグメントに翻訳結果を設定
    for segment, translation in zip(segments, translations):
        segment.translated_text = translation

    return segments


def _build_system_prompt(config: TranslationConfig) -> str:
    """
    システムプロンプトを構築する

    Args:
        config: 翻訳設定

    Returns:
        システムプロンプト文字列
    """
    prompt = f"""あなたはプロフェッショナルな翻訳者です。
以下のルールに従って、{config.source_lang} のテキストを {config.target_lang} に翻訳してください。

## ルール
1. 原文の意味を正確に伝えること
2. 自然で読みやすい {config.target_lang} にすること
3. 固有名詞・ブランド名・製品名はそのまま維持すること
4. 技術用語は一般的なカタカナ表記を使用すること
5. プレゼンテーション資料であることを考慮し、簡潔で明瞭な表現にすること
6. 箇条書きのフォーマットは維持すること
7. 数値・単位・URL はそのまま維持すること
8. 翻訳結果のみを出力し、説明や注釈は付けないこと"""

    # 用語集がある場合は追加
    if config.glossary and len(config.glossary) > 0:
        glossary_entries = "\n".join([f"- {key} → {value}" for key, value in config.glossary.items()])
        prompt += f"\n\n## 用語集\n{glossary_entries}"

    return prompt


def _build_user_prompt(segments: List[TextSegment]) -> str:
    """
    ユーザープロンプトを構築する

    Args:
        segments: 翻訳するテキストセグメントのリスト

    Returns:
        ユーザープロンプト文字列
    """
    prompt = "以下のテキストを1つずつ翻訳してください。番号付きで、翻訳結果のみを返してください。\n\n"

    for i, segment in enumerate(segments, start=1):
        prompt += f"[{i}] {segment.original_text}\n"

    return prompt


def _call_llm(
    client: OpenAI,
    system_prompt: str,
    user_prompt: str,
    config: TranslationConfig,
) -> str:
    """
    LLM を呼び出して翻訳を実行する

    Args:
        client: OpenAI クライアント
        system_prompt: システムプロンプト
        user_prompt: ユーザープロンプト
        config: 翻訳設定

    Returns:
        LLM のレスポンステキスト

    Raises:
        Exception: API 呼び出しが失敗した場合
    """
    try:
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        return response.choices[0].message.content
    except Exception as e:
        # 詳細なエラー情報を含めて再スロー
        error_details = f"Model: {config.model}, Base URL: {client.base_url}, Error: {type(e).__name__}: {str(e)}"
        raise Exception(error_details) from e


def _parse_response(response_text: str, expected_count: int) -> List[str]:
    """
    LLM のレスポンスをパースして翻訳テキストのリストを抽出する

    番号付きフォーマット [N] を正規表現で抽出する。
    パースに失敗した場合は行分割でフォールバック。

    Args:
        response_text: LLM のレスポンステキスト
        expected_count: 期待される翻訳数

    Returns:
        翻訳テキストのリスト
    """
    # 正規表現で [N] 形式を抽出
    pattern = r'\[(\d+)\]\s*(.+?)(?=\n\[\d+\]|\Z)'
    matches = re.findall(pattern, response_text, re.DOTALL)

    if len(matches) == expected_count:
        # 番号順にソートして翻訳テキストのみを返す
        sorted_matches = sorted(matches, key=lambda x: int(x[0]))
        return [text.strip() for _, text in sorted_matches]

    # フォールバック: 行分割
    lines = [line.strip() for line in response_text.strip().split('\n') if line.strip()]

    # [N] プレフィックスを除去
    cleaned_lines = []
    for line in lines:
        # [N] で始まる場合は除去
        cleaned = re.sub(r'^\[\d+\]\s*', '', line)
        cleaned_lines.append(cleaned)

    # 期待される数に合わせる
    if len(cleaned_lines) >= expected_count:
        return cleaned_lines[:expected_count]
    else:
        # 足りない場合は空文字で埋める
        return cleaned_lines + [''] * (expected_count - len(cleaned_lines))


def _translate_demo_mode(segments: List[TextSegment]) -> List[TextSegment]:
    """
    デモモード用の疑似翻訳

    LLM を使わずに、デモ用の翻訳テキストを生成する。
    ローカル環境でのテスト用。

    Args:
        segments: 翻訳するテキストセグメントのリスト

    Returns:
        疑似翻訳済みテキストが設定されたセグメントのリスト
    """
    for segment in segments:
        # デモ用の翻訳テキストを生成
        segment.translated_text = f"[デモ翻訳] {segment.original_text}"

    return segments
