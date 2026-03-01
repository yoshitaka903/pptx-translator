"""
データモデル定義

TextSegment: PPTX 内のテキスト要素を表すデータクラス
TranslationConfig: 翻訳設定を表すデータクラス
"""

from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class TextSegment:
    """
    PPTX 内の1つのテキストセグメントを表すデータクラス

    Attributes:
        original_text: 元のテキスト
        slide_index: スライドインデックス（0始まり）
        shape_index: シェイプインデックス（0始まり）
        element_type: 要素タイプ（'title', 'body', 'table', 'note', 'chart' など）
        translated_text: 翻訳後のテキスト（翻訳前は None）
        paragraph_index: パラグラフインデックス（body テキストの場合、0始まり）
        cell_row: テーブルセルの行インデックス（table の場合のみ、0始まり）
        cell_col: テーブルセルの列インデックス（table の場合のみ、0始まり）
    """
    original_text: str
    slide_index: int
    shape_index: int
    element_type: str
    translated_text: Optional[str] = None
    paragraph_index: Optional[int] = None
    cell_row: Optional[int] = None
    cell_col: Optional[int] = None

    def __post_init__(self) -> None:
        """
        バリデーション
        テーブル要素の場合は cell_row と cell_col が必須
        """
        if self.element_type == 'table':
            if self.cell_row is None or self.cell_col is None:
                raise ValueError("Table element requires cell_row and cell_col")


@dataclass
class TranslationConfig:
    """
    翻訳設定を表すデータクラス

    Attributes:
        source_lang: ソース言語（例: "English"）
        target_lang: ターゲット言語（例: "Japanese"）
        model: Foundation Model APIs のモデル名
        temperature: LLM の temperature パラメータ（0.0-1.0）
        max_tokens: 最大トークン数
        translate_notes: スピーカーノートを翻訳するか
        glossary: 用語集（キー: 原文、値: 訳語）
    """
    source_lang: str = "English"
    target_lang: str = "Japanese"
    model: str = "databricks-claude-sonnet-4-5"
    temperature: float = 0.3
    max_tokens: int = 4096
    translate_notes: bool = True
    glossary: Optional[Dict[str, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        バリデーション
        """
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("temperature must be between 0.0 and 1.0")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
