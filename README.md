# 画像・メタデータ管理API

Flask + PostgreSQL + MinIO (S3互換) で構築した画像ファイルとメタデータの管理APIです。

## 機能

- 画像ファイルのアップロードとメタデータの保存
- MD5ハッシュによる重複画像の検出とスキップ
- APIキー認証
- S3互換ストレージ（MinIO）での画像保存
- PostgreSQLでのメタデータ管理
- オプショナルなGemini APIによる画像分析

## 技術スタック

- **API**: Flask (Python)
- **データベース**: PostgreSQL
- **オブジェクトストレージ**: MinIO (S3互換)
- **コンテナ化**: Docker & Docker Compose

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd flask_sql_aws
```

### 2. 環境変数の設定

`.env`ファイルを作成し、以下の内容を設定してください：

```env
# データベース設定
POSTGRES_DB=imagedb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password

# MinIO設定
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=your_secure_secret_key
MINIO_BUCKET_NAME=images

# API設定
API_KEY=your-secret-api-key-here

# Gemini API設定（オプショナル）
GEMINI_API_KEY=your_gemini_api_key
```

### 3. アプリケーションの起動

```bash
docker-compose up -d
```

### 4. サービスの確認

- **API**: http://localhost:8000
- **MinIO Web UI**: http://localhost:9001 (ユーザー: minioadmin, パスワード: 設定したMINIO_SECRET_KEY)
- **PostgreSQL**: localhost:5432

## API利用方法

### ヘルスチェック

```bash
curl http://localhost:8000/health
```

### 画像アップロード

```bash
curl -X POST http://localhost:8000/api/upload \
  -H "X-API-Key: your-secret-api-key-here" \
  -F "image_file=@/path/to/your/image.jpg" \
  -F 'metadata={"title": "画像のタイトル", "description": "画像の説明"}'
```

### レスポンス例

#### 成功時 (201 Created)

```json
{
  "message": "Image uploaded successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "s3_key": "images/abc123def456_example.jpg",
    "md5_hash": "abc123def456789",
    "original_filename": "example.jpg",
    "mimetype": "image/jpeg",
    "filesize": 1024000,
    "uploaded_at": "2023-12-01T12:00:00Z",
    "title": "画像のタイトル",
    "description": "画像の説明",
    "gemini_analysis": "青い空と緑の草原が写っている美しい風景写真",
    "download_url": "http://localhost:9000/images/abc123def456_example.jpg?..."
  }
}
```

#### 重複画像エラー (409 Conflict)

```json
{
  "error": "Image already exists",
  "message": "An image with the same content already exists",
  "existing_image": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "s3_key": "images/abc123def456_existing.jpg",
    "title": "既存の画像",
    "description": "既に保存されている画像"
  }
}
```

#### 認証エラー (401 Unauthorized)

```json
{
  "error": "Invalid API key",
  "message": "The provided API key is not valid"
}
```

## APIエンドポイント

| エンドポイント | メソッド | 説明 | 認証 |
|---------------|---------|------|------|
| `/health` | GET | ヘルスチェック | 不要 |
| `/api/upload` | POST | 画像アップロード | 必要 |

## 認証

すべてのAPIエンドポイント（`/health`を除く）にはAPIキー認証が必要です。

リクエストヘッダーに以下を含めてください：

```
X-API-Key: your-secret-api-key-here
```

## サポートされる画像形式

- PNG (.png)
- JPEG (.jpg, .jpeg)
- GIF (.gif)
- BMP (.bmp)
- WebP (.webp)

## ファイルサイズ制限

最大アップロードサイズ: **5MB**

## PostgreSQLへの接続

```bash
docker exec -it image_api_postgres psql -U postgres -d imagedb
```

## MinIO Web UIへのアクセス

1. ブラウザで http://localhost:9001 にアクセス
2. ユーザー名: `minioadmin`
3. パスワード: 環境変数で設定した`MINIO_SECRET_KEY`

## トラブルシューティング

### サービスが起動しない場合

```bash
# ログを確認
docker-compose logs

# 特定のサービスのログを確認
docker-compose logs flask_app
docker-compose logs postgres
docker-compose logs minio
```

### データベース接続エラー

```bash
# PostgreSQLの状態を確認
docker-compose exec postgres pg_isready -U postgres
```

### MinIO接続エラー

```bash
# MinIOの状態を確認
docker-compose exec minio mc ready local
```

## 開発

### ローカル開発環境

```bash
# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
export FLASK_APP=app.app:app
export FLASK_ENV=development

# アプリケーションの起動
flask run --host=0.0.0.0 --port=5000
```

## ライセンス

MIT License

## 本番運用についての注意

このサンプルアプリケーションはローカル開発・評価用です。本番環境で使用する場合は以下の点をご考慮ください：

- セキュリティ強化（HTTPS、セキュアなAPIキー管理）
- スケーリング対応
- 監視・ログ管理
- バックアップ戦略
- AWS ECS Fargateでの運用設定 