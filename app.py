"""
PowerPoint 翻訳アプリ — Streamlit UI

英語で記述された .pptx ファイルを日本語に自動翻訳する Web アプリ。
Databricks Apps（Streamlit）上で動作。
"""

import io
import os
import streamlit as st
from pptx import Presentation

from translator.models import TranslationConfig
from translator.text_extractor import extract_texts
from translator.llm_client import create_client, translate_batch
from translator.pptx_handler import apply_translations
from translator.glossary import load_glossary


def main():
    """Streamlit アプリのメインエントリポイント"""
    st.set_page_config(
        page_title="PowerPoint 翻訳アプリ",
        layout="wide",
    )

    st.title("PowerPoint 翻訳アプリ")
    st.markdown("""
    英語で記述された PowerPoint ファイルを日本語に自動翻訳します。

    **対応要素:**
    - テキストフレーム（タイトル、本文）
    - テーブルセル
    - スピーカーノート
    - グラフタイトル
    """)

    # サイドバーで設定
    with st.sidebar:
        st.header("設定")

        # 翻訳設定
        st.subheader("翻訳設定")

        translate_notes = st.checkbox(
            "スピーカーノートも翻訳する",
            value=True,
            help="スピーカーノートを翻訳対象に含めるかどうか"
        )

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.1,
            help="翻訳の温度パラメータ（低いほど一貫性が高い）"
        )

        # 用語集のアップロード
        st.subheader("用語集（オプション）")
        st.markdown("CSV 形式の用語集をアップロードできます。")
        st.markdown("**フォーマット:** `source,target`")

        glossary_file = st.file_uploader(
            "用語集 CSV ファイル",
            type=["csv"],
            help="列名: source（原文）, target（訳語）"
        )

        glossary = {}
        if glossary_file is not None:
            try:
                glossary_bytes = io.BytesIO(glossary_file.read())
                glossary = load_glossary(glossary_bytes)
                st.success(f"用語集を読み込みました（{len(glossary)} 件）")
            except Exception as e:
                st.error(f"用語集の読み込みに失敗しました: {e}")

    # メインエリア
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("アップロード")
        uploaded_file = st.file_uploader(
            "PowerPoint ファイルを選択",
            type=["pptx"],
            help="英語で記述された .pptx ファイル"
        )

    with col2:
        st.subheader("ダウンロード")
        if uploaded_file is None:
            st.info("まずファイルをアップロードしてください")

    # 翻訳処理
    if uploaded_file is not None:
        # 翻訳ボタン
        if st.button("翻訳を開始", type="primary", use_container_width=True):
            try:
                with st.spinner("翻訳中..."):
                    # 翻訳処理を実行
                    translated_pptx = translate_pptx(
                        uploaded_file,
                        translate_notes=translate_notes,
                        temperature=temperature,
                        glossary=glossary,
                    )

                    # ダウンロードボタンを表示
                    st.success("翻訳が完了しました")

                    # 元のファイル名から新しいファイル名を生成
                    original_name = uploaded_file.name
                    if original_name.endswith(".pptx"):
                        translated_name = original_name[:-5] + "_translated.pptx"
                    else:
                        translated_name = original_name + "_translated.pptx"

                    st.download_button(
                        label="翻訳済みファイルをダウンロード",
                        data=translated_pptx,
                        file_name=translated_name,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True,
                    )

            except Exception as e:
                st.error(f"翻訳中にエラーが発生しました: {e}")
                st.exception(e)


def translate_pptx(
    uploaded_file,
    translate_notes: bool = True,
    temperature: float = 0.3,
    glossary: dict = None,
) -> bytes:
    """
    PowerPoint ファイルを翻訳する

    Args:
        uploaded_file: Streamlit の UploadedFile オブジェクト
        translate_notes: スピーカーノートを翻訳するか
        temperature: LLM の temperature パラメータ
        glossary: 用語集（オプション）

    Returns:
        翻訳済み PowerPoint ファイルのバイトデータ
    """
    # 1. ファイルを読み込む
    pptx_bytes = uploaded_file.read()
    input_buffer = io.BytesIO(pptx_bytes)
    prs = Presentation(input_buffer)

    # 2. テキストを抽出
    segments = extract_texts(prs, translate_notes=translate_notes)

    if len(segments) == 0:
        st.warning("翻訳対象のテキストが見つかりませんでした")
        # 元のファイルをそのまま返す
        output_buffer = io.BytesIO()
        prs.save(output_buffer)
        output_buffer.seek(0)
        return output_buffer.read()

    # プログレスバーを表示
    progress_text = f"テキストを抽出しました（{len(segments)} 件）"
    st.info(progress_text)

    # 3. LLM クライアントを作成
    client = create_client()

    # デモモードの警告
    if client is None:
        st.warning("""
        **デモモード**: Databricks 認証情報が設定されていないため、デモモードで動作します。

        翻訳テキストは `[デモ翻訳] 元のテキスト` の形式で生成されます。

        **本番環境で使用するには:**
        - Databricks Apps 環境にデプロイしてください
        - または、環境変数 `DATABRICKS_HOST` と `DATABRICKS_TOKEN` を設定してください
        """)

    # 4. 翻訳設定を作成
    config = TranslationConfig(
        translate_notes=translate_notes,
        temperature=temperature,
        glossary=glossary or {},
    )

    # 5. バッチ翻訳を実行（スライド単位で分割）
    all_segments = []
    slides_count = max(seg.slide_index for seg in segments) + 1

    progress_bar = st.progress(0)
    status_text = st.empty()

    for slide_idx in range(slides_count):
        # スライド単位でセグメントを取得
        slide_segments = [seg for seg in segments if seg.slide_index == slide_idx]

        if len(slide_segments) == 0:
            continue

        # 翻訳実行
        status_text.text(f"スライド {slide_idx + 1}/{slides_count} を翻訳中...")
        translated_segments = translate_batch(client, slide_segments, config)
        all_segments.extend(translated_segments)

        # プログレスバーを更新
        progress = (slide_idx + 1) / slides_count
        progress_bar.progress(progress)

    progress_bar.progress(1.0)
    status_text.text("翻訳が完了しました")

    # 6. 翻訳テキストを PPTX に書き戻す
    apply_translations(prs, all_segments)

    # 7. メモリ上で保存
    output_buffer = io.BytesIO()
    prs.save(output_buffer)
    output_buffer.seek(0)

    return output_buffer.read()


if __name__ == "__main__":
    main()
