# SPEC.md — PowerPoint 翻訳アプリ仕様

## 目的
英語で記述された .pptx ファイルを日本語に自動翻訳し、レイアウトを維持した .pptx を出力する
Databricks Apps（Streamlit）上で動作する Web アプリケーション

## 技術スタック
- Runtime: Python 3.11（Databricks Apps 環境準拠）
- UI: Streamlit >= 1.30.0
- PPTX操作: python-pptx >= 0.6.23
- LLM呼び出し: openai >= 1.0.0（Databricks Foundation Model APIs の OpenAI 互換エンドポイント）
- 認証: databricks-sdk >= 0.20.0（環境変数 DATABRICKS_HOST から自動取得）
- テスト: pytest + pytest-mock

## モジュール構成
| ファイル | 責務 | 依存 |
|---------|------|------|
| translator/models.py | TextSegment, TranslationConfig のデータクラス定義 | なし |
| translator/text_extractor.py | PPTX からテキストセグメントを抽出 | python-pptx, models |
| translator/llm_client.py | Foundation Model APIs への翻訳リクエスト | openai, databricks-sdk, models |
| translator/pptx_handler.py | 翻訳済みテキストを PPTX に書き戻す | python-pptx, models |
| translator/glossary.py | CSV 用語集の読み込み | pandas |
| app.py | Streamlit UI・ワークフロー制御 | 上記すべて |

## 実装順序（この順番で実装すること）
1. translator/models.py
2. translator/text_extractor.py + tests/test_text_extractor.py
3. translator/llm_client.py + tests/test_llm_client.py
4. translator/pptx_handler.py + tests/test_pptx_handler.py
5. translator/glossary.py
6. app.py（UI統合）
7. requirements.txt, .gitignore

## データフロー
Upload(.pptx)
→ extract_texts(Presentation) → List[TextSegment]
→ translate_batch(client, segments, config) → List[TextSegment] (translated)
→ apply_translations(Presentation, segments) → Presentation
→ prs.save(BytesIO) → Download

## 翻訳ルール
- スライド単位でバッチ翻訳（文脈一貫性のため）
- 番号付きリスト形式で LLM に送信し、番号付きで返却させる
- temperature: 0.3（翻訳は低温推奨）
- 固有名詞・プログラミングコード・数値・URL はそのまま維持
- 用語集がある場合はシステムプロンプトに埋め込む

## 翻訳対象
- テキストフレーム（タイトル、本文）: ✅
- テーブルセル: ✅
- スピーカーノート: ✅（設定で ON/OFF）
- グラフタイトル: ✅
- SmartArt: ❌（python-pptx の制限）
- 画像内テキスト: ❌

## スタイル維持戦略
翻訳テキストを書き戻す際、パラグラフの最初の Run のスタイルを保持し、
翻訳テキスト全体をその Run に設定する。残りの Run は空文字にする。

## エラーハンドリング
- LLM 呼び出し失敗: 最大2回リトライ（Exponential Backoff）
- レスポンスパース失敗: 行分割のフォールバック
- PPTX 読み込み失敗: Streamlit でエラー表示