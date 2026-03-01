# ARCHITECTURE.md

## システム構成
Databricks Apps (Serverless) 上で Streamlit を実行。
翻訳処理は Foundation Model APIs (Pay-per-token) を OpenAI 互換クライアントで呼び出す。
ファイルはメモリ上（io.BytesIO）のみで処理し、ディスクに保存しない。

## 認証フロー
1. Databricks Apps 環境では `DATABRICKS_HOST` が自動設定される
2. `databricks.sdk.core.Config()` が環境変数から認証情報を自動取得
3. OpenAI クライアントに `base_url` と `api_key` を渡す
```python
from databricks.sdk.core import Config
from openai import OpenAI

cfg = Config()
client = OpenAI(
    base_url=f"https://{cfg.host}/serving-endpoints",
    api_key=cfg.token,
)
```

## Streamlit ファイル I/O パターン
- アップロード: `st.file_uploader("...", type=["pptx"])`
  → `uploaded_file.read()` で bytes 取得 → `io.BytesIO` で Presentation に渡す
- ダウンロード: `prs.save(output_buffer)` → `st.download_button(data=output_buffer)`

## Foundation Model APIs 呼び出しパターン
- エンドポイント: `databricks-claude-sonnet-4-5`（推奨）
- API: OpenAI Chat Completions 互換
- システムプロンプトで翻訳ルール・用語集を注入
- ユーザープロンプトに番号付きテキストリストを送信