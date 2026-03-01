# PowerPoint 翻訳アプリ — Databricks Apps

## プロジェクト概要
英語で記述された .pptx ファイルを日本語に自動翻訳する Web アプリ。Databricks Apps（Streamlit）上で動作。
翻訳には Foundation Model APIs（OpenAI 互換エンドポイント）を使用。

## 仕様書
- 全体仕様: @SPEC.md
- アーキテクチャ: @docs/ARCHITECTURE.md
- プロンプト設計: @docs/TRANSLATION_PROMPT.md

## 技術スタック
- Python 3.11, Streamlit, python-pptx, openai, databricks-sdk
- テスト: pytest + pytest-mock
- デプロイ: Databricks Asset Bundles

## ディレクトリ構成
- `app.py`: Streamlit メインアプリ（エントリポイント）
- `translator/`: ビジネスロジック（models, text_extractor, llm_client, pptx_handler, glossary）
- `tests/`: pytest テスト
- `fixtures/`: テスト用サンプルファイル

## コマンド
- ローカル実行: `streamlit run app.py`
- テスト: `python -m pytest tests/ -v --tb=short`
- 単体テスト: `python -m pytest tests/test_<module>.py -v`
- リント: `python -m py_compile translator/<module>.py`
- DAB デプロイ: `databricks bundle deploy && databricks apps deploy pptx-translator`

## コーディング規約
- 型ヒントを全関数に付ける
- docstring は日本語で書く
- import は標準ライブラリ → サードパーティ → ローカルの順
- f-string を使う（.format() は使わない）
- ファイルはディスクに保存しない（io.BytesIO のみ）

## 重要な注意点
- Databricks Apps のファイルサイズ上限は 10MB（ソースコード全体）
- python-pptx は SmartArt のテキスト編集を未サポート
- ai_translate() は日本語未対応のため使わない（Foundation Model APIs を直接呼ぶ）
- LLM レスポンスのパースは正規表現で [N] 形式を抽出、フォールバックあり
- Run のスタイル維持: 最初の Run に翻訳テキスト設定、残りは空文字

## Git ワークフロー
- feature ブランチで作業（main 直接コミット禁止）
- コミットメッセージ: `feat:`, `fix:`, `test:`, `docs:` プレフィックス