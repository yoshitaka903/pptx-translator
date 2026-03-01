# PowerPoint 翻訳アプリ

英語で記述された PowerPoint ファイルを日本語に自動翻訳する Web アプリ。
Databricks Apps（Streamlit）上で動作し、Foundation Model APIs（Claude）を使用します。

## 機能

- ✅ テキストフレーム（タイトル、本文）の翻訳
- ✅ テーブルセルの翻訳
- ✅ スピーカーノートの翻訳（ON/OFF 可能）
- ✅ グラフタイトルの翻訳
- ✅ CSV 用語集のアップロード（オプション）
- ✅ スタイル（フォント、サイズ、色）の維持

## デプロイ方法（Databricks Apps）

### 前提条件

1. Databricks CLI v0.200 以上がインストールされていること
2. Foundation Model APIs にアクセス可能なワークスペース
3. `databricks-claude-sonnet-4-5` エンドポイントへのアクセス権限

### 手順

#### 1. Databricks CLI の認証設定

```bash
databricks auth login --host https://<your-workspace>.databricks.com
```

#### 2. Asset Bundle の検証

```bash
databricks bundle validate
```

#### 3. デプロイ（開発環境）

```bash
databricks bundle deploy -t dev
```

#### 4. アプリの起動

```bash
databricks apps deploy pptx-translator --source-code-path .
```

#### 5. アプリへのアクセス

デプロイ後、Databricks ワークスペースの Apps セクションからアプリにアクセスできます。

```
https://<your-workspace>.databricks.com/apps/pptx-translator
```

## ローカル開発（デモモード）

Databricks 認証なしでローカル環境でテストできます（デモモード）。

### 1. 仮想環境の作成

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. アプリの起動

```bash
streamlit run app.py
```

**注意:** ローカル環境では `[デモ翻訳] 元のテキスト` 形式の疑似翻訳が生成されます。

## ローカル開発（実翻訳）

環境変数を設定すれば、ローカル環境でも実翻訳が可能です。

```bash
export DATABRICKS_HOST="your-workspace.databricks.com"
export DATABRICKS_TOKEN="dapi..."
streamlit run app.py
```

## テスト

```bash
# 全テストの実行
python -m pytest tests/ -v

# 特定のモジュールのテスト
python -m pytest tests/test_text_extractor.py -v

# カバレッジレポートの生成
pip install pytest-cov
python -m pytest tests/ --cov=translator --cov-report=html
```

## プロジェクト構成

```
pptx-translator/
├── app.py                      # Streamlit メインアプリ
├── translator/                 # ビジネスロジック
│   ├── models.py              # データモデル
│   ├── text_extractor.py      # テキスト抽出
│   ├── llm_client.py          # LLM 翻訳クライアント
│   ├── pptx_handler.py        # 翻訳書き戻し
│   └── glossary.py            # 用語集読み込み
├── tests/                      # pytest テスト
│   ├── test_text_extractor.py
│   ├── test_llm_client.py
│   ├── test_pptx_handler.py
│   └── test_glossary.py
├── docs/                       # ドキュメント
│   ├── ARCHITECTURE.md
│   └── TRANSLATION_PROMPT.md
├── databricks.yml             # Asset Bundle 設定
├── requirements.txt           # 依存ライブラリ
└── README.md                  # このファイル
```

## 技術スタック

- **Runtime**: Python 3.11
- **UI**: Streamlit 1.54.0
- **PPTX 操作**: python-pptx 1.0.2
- **LLM**: OpenAI 2.24.0（Databricks Foundation Model APIs 互換）
- **認証**: databricks-sdk 0.94.0
- **用語集**: pandas 2.3.3
- **テスト**: pytest 9.0.2

## 制限事項

- SmartArt のテキストは翻訳対象外（python-pptx の制限）
- 画像内のテキストは翻訳対象外
- ファイルサイズ上限: 10MB（Databricks Apps の制限）

## トラブルシューティング

### "ValueError: shape is not a placeholder"

→ 修正済み（v1.0.0 以降）

### "Connection error" / "LLM call failed"

ローカル環境の場合:
- デモモードで動作します（`[デモ翻訳] ...` 形式）
- 実翻訳するには環境変数 `DATABRICKS_HOST` と `DATABRICKS_TOKEN` を設定

Databricks Apps 環境の場合:
- Foundation Model APIs へのアクセス権限を確認
- `databricks-claude-sonnet-4-5` エンドポイントが利用可能か確認

## ライセンス

このプロジェクトは検証用サンプルです。
