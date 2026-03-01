"""
CSV 用語集の読み込みモジュール

CSV ファイルまたは io.BytesIO から用語集を読み込み、
Dict[str, str] 形式（キー: 原文、値: 訳語）で返す。
"""

import io
from typing import Dict, Union, Optional
import pandas as pd


def load_glossary(
    source: Union[str, io.BytesIO],
    source_col: str = "source",
    target_col: str = "target",
) -> Dict[str, str]:
    """
    CSV 用語集を読み込む

    CSV フォーマット:
    - ヘッダー行が必須
    - source_col: 原文の列名（デフォルト: "source"）
    - target_col: 訳語の列名（デフォルト: "target"）

    例:
    ```csv
    source,target
    AI,人工知能
    ML,機械学習
    ```

    Args:
        source: CSV ファイルパス（str）または io.BytesIO オブジェクト
        source_col: 原文の列名
        target_col: 訳語の列名

    Returns:
        用語集の辞書（キー: 原文、値: 訳語）

    Raises:
        ValueError: 指定された列が存在しない場合
        FileNotFoundError: ファイルが存在しない場合（str の場合）
        pd.errors.EmptyDataError: CSV が空の場合
    """
    try:
        # pandas で CSV を読み込む
        df = pd.read_csv(source)

        # 列の存在チェック
        if source_col not in df.columns:
            raise ValueError(f"Column '{source_col}' not found in CSV. Available columns: {list(df.columns)}")
        if target_col not in df.columns:
            raise ValueError(f"Column '{target_col}' not found in CSV. Available columns: {list(df.columns)}")

        # NaN を除外して辞書に変換
        glossary = {}
        for _, row in df.iterrows():
            source_text = row[source_col]
            target_text = row[target_col]

            # NaN または空文字列をスキップ
            if pd.notna(source_text) and pd.notna(target_text):
                source_str = str(source_text).strip()
                target_str = str(target_text).strip()

                if source_str and target_str:
                    glossary[source_str] = target_str

        return glossary

    except FileNotFoundError:
        raise FileNotFoundError(f"Glossary file not found: {source}")
    except pd.errors.EmptyDataError:
        raise pd.errors.EmptyDataError("CSV file is empty")


def create_glossary_from_dict(mapping: Dict[str, str]) -> Dict[str, str]:
    """
    辞書から用語集を作成する（ユーティリティ関数）

    空文字列や None をフィルタリングする。

    Args:
        mapping: 原文 -> 訳語のマッピング

    Returns:
        フィルタリングされた用語集
    """
    glossary = {}
    for key, value in mapping.items():
        if key and value:
            key_str = str(key).strip()
            value_str = str(value).strip()
            if key_str and value_str:
                glossary[key_str] = value_str

    return glossary
