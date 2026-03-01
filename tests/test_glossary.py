"""
glossary.py のテスト
"""

import io
import pytest
import pandas as pd

from translator.glossary import load_glossary, create_glossary_from_dict


class TestLoadGlossary:
    """load_glossary 関数のテスト"""

    def test_load_from_bytesio(self):
        """io.BytesIO から用語集を読み込める"""
        csv_content = """source,target
AI,人工知能
ML,機械学習
Deep Learning,深層学習"""

        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))

        glossary = load_glossary(csv_bytes)

        assert len(glossary) == 3
        assert glossary["AI"] == "人工知能"
        assert glossary["ML"] == "機械学習"
        assert glossary["Deep Learning"] == "深層学習"

    def test_load_with_custom_columns(self):
        """カスタム列名を使用できる"""
        csv_content = """english,japanese
AI,人工知能
ML,機械学習"""

        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))

        glossary = load_glossary(csv_bytes, source_col="english", target_col="japanese")

        assert len(glossary) == 2
        assert glossary["AI"] == "人工知能"
        assert glossary["ML"] == "機械学習"

    def test_skip_nan_values(self):
        """NaN 値をスキップする"""
        csv_content = """source,target
AI,人工知能
ML,
,機械学習
Deep Learning,深層学習"""

        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))

        glossary = load_glossary(csv_bytes)

        # NaN を含む行はスキップされる
        assert len(glossary) == 2
        assert glossary["AI"] == "人工知能"
        assert glossary["Deep Learning"] == "深層学習"

    def test_skip_empty_strings(self):
        """空文字列をスキップする"""
        csv_content = """source,target
AI,人工知能
  ," "
" "," "
ML,機械学習"""

        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))

        glossary = load_glossary(csv_bytes)

        # 空文字列やスペースのみの行はスキップされる
        assert len(glossary) == 2
        assert glossary["AI"] == "人工知能"
        assert glossary["ML"] == "機械学習"

    def test_strip_whitespace(self):
        """前後の空白を除去する"""
        csv_content = """source,target
  AI  ,  人工知能
ML,機械学習"""

        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))

        glossary = load_glossary(csv_bytes)

        # 空白が除去される
        assert glossary["AI"] == "人工知能"
        assert glossary["ML"] == "機械学習"

    def test_missing_source_column(self):
        """source 列がない場合はエラー"""
        csv_content = """wrong_col,target
AI,人工知能"""

        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))

        with pytest.raises(ValueError) as exc_info:
            load_glossary(csv_bytes)

        assert "Column 'source' not found" in str(exc_info.value)
        assert "wrong_col" in str(exc_info.value)

    def test_missing_target_column(self):
        """target 列がない場合はエラー"""
        csv_content = """source,wrong_col
AI,人工知能"""

        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))

        with pytest.raises(ValueError) as exc_info:
            load_glossary(csv_bytes)

        assert "Column 'target' not found" in str(exc_info.value)

    def test_empty_csv(self):
        """空の CSV の場合はエラー"""
        csv_content = ""

        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))

        with pytest.raises(pd.errors.EmptyDataError):
            load_glossary(csv_bytes)

    def test_header_only_csv(self):
        """ヘッダーのみの CSV の場合は空の辞書を返す"""
        csv_content = """source,target"""

        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))

        glossary = load_glossary(csv_bytes)

        assert len(glossary) == 0

    def test_load_from_file(self, tmp_path):
        """ファイルパスから用語集を読み込める"""
        # 一時ファイルを作成
        csv_file = tmp_path / "glossary.csv"
        csv_file.write_text("""source,target
AI,人工知能
ML,機械学習""", encoding='utf-8')

        glossary = load_glossary(str(csv_file))

        assert len(glossary) == 2
        assert glossary["AI"] == "人工知能"
        assert glossary["ML"] == "機械学習"

    def test_file_not_found(self):
        """存在しないファイルの場合はエラー"""
        with pytest.raises(FileNotFoundError):
            load_glossary("/nonexistent/path/to/file.csv")

    def test_duplicate_keys(self):
        """重複するキーの場合は後勝ち"""
        csv_content = """source,target
AI,人工知能
AI,エーアイ"""

        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))

        glossary = load_glossary(csv_bytes)

        # 後の行が優先される
        assert glossary["AI"] == "エーアイ"

    def test_numeric_values(self):
        """数値も文字列として扱われる"""
        csv_content = """source,target
123,456
AI,人工知能"""

        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))

        glossary = load_glossary(csv_bytes)

        assert glossary["123"] == "456"
        assert glossary["AI"] == "人工知能"


class TestCreateGlossaryFromDict:
    """create_glossary_from_dict 関数のテスト"""

    def test_basic_dict(self):
        """基本的な辞書から用語集を作成できる"""
        mapping = {
            "AI": "人工知能",
            "ML": "機械学習",
        }

        glossary = create_glossary_from_dict(mapping)

        assert len(glossary) == 2
        assert glossary["AI"] == "人工知能"
        assert glossary["ML"] == "機械学習"

    def test_filter_empty_keys(self):
        """空のキーをフィルタリングする"""
        mapping = {
            "AI": "人工知能",
            "": "空キー",
            None: "None キー",
        }

        glossary = create_glossary_from_dict(mapping)

        assert len(glossary) == 1
        assert glossary["AI"] == "人工知能"

    def test_filter_empty_values(self):
        """空の値をフィルタリングする"""
        mapping = {
            "AI": "人工知能",
            "ML": "",
            "DL": None,
        }

        glossary = create_glossary_from_dict(mapping)

        assert len(glossary) == 1
        assert glossary["AI"] == "人工知能"

    def test_strip_whitespace(self):
        """前後の空白を除去する"""
        mapping = {
            "  AI  ": "  人工知能  ",
            "ML": "機械学習",
        }

        glossary = create_glossary_from_dict(mapping)

        assert glossary["AI"] == "人工知能"
        assert glossary["ML"] == "機械学習"

    def test_empty_dict(self):
        """空の辞書の場合は空の用語集を返す"""
        mapping = {}

        glossary = create_glossary_from_dict(mapping)

        assert len(glossary) == 0

    def test_numeric_values(self):
        """数値も文字列として扱われる"""
        mapping = {
            123: 456,
            "AI": "人工知能",
        }

        glossary = create_glossary_from_dict(mapping)

        assert glossary["123"] == "456"
        assert glossary["AI"] == "人工知能"
