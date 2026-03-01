"""
llm_client.py のテスト
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from openai import OpenAI

from translator.llm_client import (
    create_client,
    translate_batch,
    _build_system_prompt,
    _build_user_prompt,
    _call_llm,
    _parse_response,
    _translate_demo_mode,
)
from translator.models import TextSegment, TranslationConfig


@pytest.fixture
def mock_openai_client():
    """モック OpenAI クライアントを作成する"""
    return Mock(spec=OpenAI)


@pytest.fixture
def sample_segments():
    """サンプルのテキストセグメントを作成する"""
    return [
        TextSegment(
            original_text="Hello World",
            slide_index=0,
            shape_index=0,
            element_type="title",
        ),
        TextSegment(
            original_text="This is a test",
            slide_index=0,
            shape_index=1,
            element_type="body",
        ),
        TextSegment(
            original_text="Welcome to our presentation",
            slide_index=1,
            shape_index=0,
            element_type="title",
        ),
    ]


@pytest.fixture
def default_config():
    """デフォルトの翻訳設定を作成する"""
    return TranslationConfig()


class TestCreateClient:
    """create_client 関数のテスト"""

    @patch('translator.llm_client.Config')
    @patch('translator.llm_client.OpenAI')
    def test_create_client(self, mock_openai_class, mock_config_class):
        """クライアントが正しく作成される"""
        # モックの設定
        mock_cfg = Mock()
        mock_cfg.host = "example.databricks.com"
        mock_cfg.token = "test-token"
        mock_config_class.return_value = mock_cfg

        # 関数を呼び出し
        create_client()

        # OpenAI が正しいパラメータで呼ばれたことを確認
        mock_openai_class.assert_called_once_with(
            base_url="https://example.databricks.com/serving-endpoints",
            api_key="test-token",
        )


class TestTranslateBatch:
    """translate_batch 関数のテスト"""

    def test_empty_segments(self, mock_openai_client, default_config):
        """空のセグメントリストの場合は何もしない"""
        segments = []
        result = translate_batch(mock_openai_client, segments, default_config)

        assert result == []
        # LLM は呼ばれない
        assert not mock_openai_client.chat.completions.create.called

    def test_successful_translation(self, mock_openai_client, sample_segments, default_config):
        """正常に翻訳できる"""
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """[1] こんにちは世界
[2] これはテストです
[3] プレゼンテーションへようこそ"""

        mock_openai_client.chat.completions.create.return_value = mock_response

        # 翻訳実行
        result = translate_batch(mock_openai_client, sample_segments, default_config)

        # 結果の検証
        assert len(result) == 3
        assert result[0].translated_text == "こんにちは世界"
        assert result[1].translated_text == "これはテストです"
        assert result[2].translated_text == "プレゼンテーションへようこそ"

        # 元のテキストは変更されていない
        assert result[0].original_text == "Hello World"

    def test_retry_on_failure(self, mock_openai_client, sample_segments, default_config):
        """失敗時にリトライする"""
        # 1回目は失敗、2回目は成功
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """[1] こんにちは世界
[2] これはテストです
[3] プレゼンテーションへようこそ"""

        mock_openai_client.chat.completions.create.side_effect = [
            Exception("API Error"),
            mock_response,
        ]

        # 翻訳実行
        result = translate_batch(mock_openai_client, sample_segments, default_config, max_retries=2)

        # 結果の検証
        assert len(result) == 3
        assert result[0].translated_text == "こんにちは世界"

        # 2回呼ばれたことを確認
        assert mock_openai_client.chat.completions.create.call_count == 2

    def test_max_retries_exceeded(self, mock_openai_client, sample_segments, default_config):
        """最大リトライ回数を超えた場合は例外を投げる"""
        # 常に失敗
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

        # 例外が投げられることを確認
        with pytest.raises(Exception) as exc_info:
            translate_batch(mock_openai_client, sample_segments, default_config, max_retries=1)

        assert "failed after 2 attempts" in str(exc_info.value)


class TestBuildSystemPrompt:
    """_build_system_prompt 関数のテスト"""

    def test_basic_prompt(self, default_config):
        """基本的なシステムプロンプトが生成される"""
        prompt = _build_system_prompt(default_config)

        assert "プロフェッショナルな翻訳者" in prompt
        assert "English" in prompt
        assert "Japanese" in prompt
        assert "ルール" in prompt

    def test_prompt_with_glossary(self):
        """用語集がある場合はプロンプトに含まれる"""
        config = TranslationConfig(
            glossary={"AI": "人工知能", "ML": "機械学習"}
        )

        prompt = _build_system_prompt(config)

        assert "用語集" in prompt
        assert "AI → 人工知能" in prompt
        assert "ML → 機械学習" in prompt

    def test_prompt_without_glossary(self, default_config):
        """用語集がない場合は用語集セクションが含まれない"""
        prompt = _build_system_prompt(default_config)

        assert "用語集" not in prompt


class TestBuildUserPrompt:
    """_build_user_prompt 関数のテスト"""

    def test_user_prompt_format(self, sample_segments):
        """ユーザープロンプトが正しいフォーマットで生成される"""
        prompt = _build_user_prompt(sample_segments)

        assert "[1] Hello World" in prompt
        assert "[2] This is a test" in prompt
        assert "[3] Welcome to our presentation" in prompt
        assert "番号付きで、翻訳結果のみを返してください" in prompt


class TestCallLLM:
    """_call_llm 関数のテスト"""

    def test_call_llm_success(self, mock_openai_client, default_config):
        """LLM 呼び出しが成功する"""
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "翻訳結果"

        mock_openai_client.chat.completions.create.return_value = mock_response

        # 呼び出し
        result = _call_llm(
            mock_openai_client,
            "system prompt",
            "user prompt",
            default_config,
        )

        # 結果の検証
        assert result == "翻訳結果"

        # 正しいパラメータで呼ばれたことを確認
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs['model'] == default_config.model
        assert call_args.kwargs['temperature'] == default_config.temperature
        assert call_args.kwargs['max_tokens'] == default_config.max_tokens
        assert len(call_args.kwargs['messages']) == 2


class TestParseResponse:
    """_parse_response 関数のテスト"""

    def test_parse_numbered_format(self):
        """番号付きフォーマットを正しくパースできる"""
        response = """[1] こんにちは世界
[2] これはテストです
[3] プレゼンテーションへようこそ"""

        result = _parse_response(response, 3)

        assert len(result) == 3
        assert result[0] == "こんにちは世界"
        assert result[1] == "これはテストです"
        assert result[2] == "プレゼンテーションへようこそ"

    def test_parse_numbered_format_with_newlines(self):
        """複数行にまたがる翻訳も正しくパースできる"""
        response = """[1] こんにちは世界
これは複数行です
[2] これはテストです
[3] 最後の項目"""

        result = _parse_response(response, 3)

        assert len(result) == 3
        assert "こんにちは世界" in result[0]
        assert "複数行" in result[0]

    def test_parse_fallback_to_lines(self):
        """番号なしフォーマットの場合は行分割でフォールバック"""
        response = """こんにちは世界
これはテストです
プレゼンテーションへようこそ"""

        result = _parse_response(response, 3)

        assert len(result) == 3
        assert result[0] == "こんにちは世界"
        assert result[1] == "これはテストです"
        assert result[2] == "プレゼンテーションへようこそ"

    def test_parse_mixed_format(self):
        """[N] プレフィックスを除去してフォールバック"""
        response = """[1] こんにちは世界
[2] これはテストです"""

        result = _parse_response(response, 2)

        assert len(result) == 2
        assert result[0] == "こんにちは世界"
        assert result[1] == "これはテストです"

    def test_parse_insufficient_lines(self):
        """翻訳数が足りない場合は空文字で埋める"""
        response = """[1] こんにちは世界"""

        result = _parse_response(response, 3)

        assert len(result) == 3
        assert result[0] == "こんにちは世界"
        assert result[1] == ""
        assert result[2] == ""

    def test_parse_excess_lines(self):
        """翻訳数が多い場合は期待数に切り詰める"""
        response = """[1] こんにちは世界
[2] これはテストです
[3] プレゼンテーションへようこそ
[4] 余分な項目"""

        result = _parse_response(response, 3)

        assert len(result) == 3
        assert result[0] == "こんにちは世界"
        assert result[1] == "これはテストです"
        assert result[2] == "プレゼンテーションへようこそ"


class TestDemoMode:
    """デモモードのテスト"""

    def test_translate_demo_mode(self, sample_segments):
        """デモモードで疑似翻訳できる"""
        result = _translate_demo_mode(sample_segments)

        assert len(result) == 3
        assert result[0].translated_text == "[デモ翻訳] Hello World"
        assert result[1].translated_text == "[デモ翻訳] This is a test"
        assert result[2].translated_text == "[デモ翻訳] Welcome to our presentation"

    def test_translate_batch_with_none_client(self, sample_segments, default_config):
        """client が None の場合はデモモードで動作する"""
        result = translate_batch(None, sample_segments, default_config)

        assert len(result) == 3
        assert all(seg.translated_text is not None for seg in result)
        assert all("[デモ翻訳]" in seg.translated_text for seg in result)
