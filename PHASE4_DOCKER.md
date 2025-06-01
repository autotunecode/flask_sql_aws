# 🐳 Phase 4: Docker化とマルチコンテナ環境

## Dockerとは？
**Docker**はアプリケーションを軽量なコンテナに梱包する技術です。コンテナには、アプリケーションの実行に必要なライブラリ、依存関係、設定がすべて含まれており、どの環境でも同じように動作することを保証します。

## Docker Composeとは？
**Docker Compose**は複数のDockerコンテナで構成されるアプリケーションを定義・実行するツールです。YAMLファイルでサービスを設定し、単一のコマンドでマルチコンテナアプリケーション全体を起動できます。

---

## 🎯 Phase 4の学習目標
- Dockerの基本概念とDockerfileの書き方を理解
- Docker Composeによるマルチコンテナ環境の構築
- 環境変数とシークレット管理の実装
- ネットワークとボリュームの設定
- 本番環境対応のコンテナ設定

---

## 📦 Step 4.1: Dockerfileの作成

### Flaskアプリケーション用Dockerfile

#### `Dockerfile` を作成
```dockerfile
# Dockerfile - Flaskアプリケーション用コンテナ定義
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージの更新とcurlのインストール（ヘルスチェック用）
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY app/ ./app/

# ポート5000を公開
EXPOSE 5000

# 非rootユーザーを作成してセキュリティを向上
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# ヘルスチェック設定
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Gunicorn WSGIサーバーでアプリケーションを起動
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app.app:app"]
```

**🎓 学習ポイント**:
- `FROM`: ベースイメージの指定
- `WORKDIR`: コンテナ内の作業ディレクトリ
- `COPY` vs `ADD`: ファイルのコピー方法
- `RUN`: ビルド時にコマンド実行
- `EXPOSE`: ポート公開の宣言
- `USER`: セキュリティのため非rootユーザー使用
- `HEALTHCHECK`: コンテナの健康状態監視
- `CMD`: コンテナ起動時のデフォルトコマンド

### requirements.txtの更新

#### `requirements.txt` を本番用に更新
```txt
# requirements.txt - 本番環境用依存関係
Flask==2.3.3
Flask-CORS==4.0.0
psycopg2-binary==2.9.7
boto3==1.34.34
Pillow==10.2.0
python-dotenv==1.0.1
gunicorn==21.2.0
requests==2.32.3

# セキュリティとロギング強化
python-json-logger==2.0.7
```

---

## 🔧 Step 4.2: Docker Compose設定

### マルチコンテナ環境の定義

#### `docker-compose.yml` を作成
```yaml
# docker-compose.yml - マルチコンテナアプリケーション定義
version: '3.8'

services:
  # PostgreSQLデータベース
  postgres:
    image: postgres:15-alpine
    container_name: image_api_postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      # データ永続化
      - postgres_data:/var/lib/postgresql/data
      # 初期化スクリプト
      - ./init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network
    restart: unless-stopped

  # MinIOオブジェクトストレージ
  minio:
    image: minio/minio:latest
    container_name: image_api_minio
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      # データ永続化
      - minio_data:/data
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
    networks:
      - app-network
    restart: unless-stopped

  # Flaskアプリケーション
  flask_app:
    build: .
    container_name: image_api_flask
    environment:
      # データベース設定
      DB_HOST: postgres
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      
      # MinIO設定
      MINIO_ENDPOINT_URL: http://minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      MINIO_BUCKET_NAME: ${MINIO_BUCKET_NAME}
      
      # API設定
      API_KEY: ${API_KEY}
      SECRET_KEY: ${SECRET_KEY}
      
      # オプション: Gemini API
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      
      # Flask設定
      FLASK_ENV: production
    ports:
      - "8000:5000"
    depends_on:
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - app-network
    restart: unless-stopped
    # リソース制限
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

# ネットワーク定義
networks:
  app-network:
    driver: bridge

# ボリューム定義
volumes:
  postgres_data:
    driver: local
  minio_data:
    driver: local
```

**🎓 学習ポイント**:
- `services`: 各コンテナサービスの定義
- `depends_on`: サービス間の依存関係
- `healthcheck`: サービス健康状態の監視
- `networks`: コンテナ間の通信設定
- `volumes`: データ永続化の設定
- `environment`: 環境変数の設定
- `restart`: 自動再起動ポリシー

### 環境変数ファイルの作成

#### `.env.example` を作成（テンプレート）
```bash
# .env.example - 環境変数テンプレート
# 本ファイルをコピーして .env を作成し、値を設定してください

# データベース設定
POSTGRES_DB=imagedb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_123

# MinIO設定
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_NAME=images

# API設定
API_KEY=your-api-key-here
SECRET_KEY=your-secret-key-here

# オプション: Gemini API（AIによる画像分析機能）
GEMINI_API_KEY=
```

#### 実際の `.env` ファイルを作成
```bash
# .env ファイルを作成（.env.exampleをコピー）
cp .env.example .env

# .envファイルを編集して実際の値を設定
# 注意: .envファイルはGitにコミットしないでください
```

---

## 🔒 Step 4.3: セキュリティとベストプラクティス

### .dockerignoreファイルの作成

#### `.dockerignore` を作成
```
# .dockerignore - Dockerビルド時に除外するファイル
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.git
.gitignore
README.md
TUTORIAL.md
PHASE*.md
.env
.env.*
.pytest_cache/
.coverage
htmlcov/
.tox/
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.DS_Store
.vscode/
.idea/
*.swp
*.swo
*~
test_*.py
stress_test_*.py
```

### ログ設定の改善

#### `app/config.py` にログ設定を追加
```python
# app/config.py にログ設定を追加
import logging
import os
from pythonjsonlogger import jsonlogger

class Config:
    # ... existing config ...
    
    # ログ設定
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @staticmethod
    def init_logging():
        """本番環境対応のログ設定"""
        log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
        
        # JSON形式のログフォーマッター（本番環境向け）
        if os.getenv('FLASK_ENV') == 'production':
            formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # ルートロガーの設定
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        
        logging.basicConfig(
            level=log_level,
            handlers=[handler],
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
```

---

## 🚀 Step 4.4: Docker環境での起動とテスト

### アプリケーションの構築・起動

#### 初回セットアップ
```bash
# 1. 環境変数ファイルを準備
cp .env.example .env
# .envファイルを編集して適切な値を設定

# 2. 既存の個別コンテナがあれば停止・削除
docker stop postgres-dev minio-dev 2>/dev/null || true
docker rm postgres-dev minio-dev 2>/dev/null || true

# 3. Docker Composeでアプリケーション全体を構築・起動
docker compose up --build -d

# 4. ログの確認
docker compose logs -f
```

#### サービス状態の確認
```bash
# 全サービスの状態確認
docker compose ps

# 個別サービスのログ確認
docker compose logs flask_app
docker compose logs postgres
docker compose logs minio

# ヘルスチェック状態の確認
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

### 🧪 統合テストの実行

#### `test_docker_integration.py` を作成
```python
# test_docker_integration.py - Docker環境統合テスト
import requests
import json
import io
import time
from PIL import Image, ImageDraw

# Docker環境設定
API_BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key-here"  # .envファイルのAPI_KEYと同じ値

def wait_for_services(max_wait=120):
    """サービスが起動するまで待機"""
    print("🕐 サービス起動待機中...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print("✅ サービス起動完了")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(5)
        print("   まだ起動中...")
    
    print("❌ サービス起動タイムアウト")
    return False

def test_full_integration():
    """完全統合テスト"""
    print("🐳 Docker環境統合テスト開始")
    
    # サービス起動待機
    if not wait_for_services():
        return False
    
    # 1. ヘルスチェック
    print("1. ヘルスチェック...")
    response = requests.get(f"{API_BASE_URL}/health")
    if response.status_code == 200:
        print("✅ Flask APIが正常に動作")
    else:
        print("❌ Flask APIエラー")
        return False
    
    # 2. データベース接続確認
    print("2. データベース接続確認...")
    headers = {'X-API-Key': API_KEY}
    response = requests.get(f"{API_BASE_URL}/api/database/status", headers=headers)
    if response.status_code == 200:
        print("✅ PostgreSQL接続成功")
    else:
        print("❌ PostgreSQL接続失敗")
        return False
    
    # 3. 画像アップロードテスト
    print("3. 画像アップロードテスト...")
    
    # テスト画像作成
    img = Image.new('RGB', (400, 300), color='lightgreen')
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "Docker Integration Test", fill='darkblue')
    draw.text((50, 80), f"Timestamp: {int(time.time())}", fill='red')
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    # アップロード実行
    metadata = {
        "title": "Docker統合テスト画像",
        "description": "Docker Composeによる統合環境でのテスト画像です。",
        "category": "integration_test"
    }
    
    files = {'image_file': ('docker_test.jpg', img_bytes, 'image/jpeg')}
    data = {'metadata': json.dumps(metadata)}
    
    response = requests.post(f"{API_BASE_URL}/api/upload", files=files, data=data, headers=headers)
    
    if response.status_code == 201:
        print("✅ 画像アップロード成功")
        upload_data = response.json()['data']
        print(f"   画像ID: {upload_data['id']}")
        print(f"   S3キー: {upload_data['s3_key']}")
        
        # 4. 画像一覧取得テスト
        print("4. 画像一覧取得テスト...")
        response = requests.get(f"{API_BASE_URL}/api/images", headers=headers)
        if response.status_code == 200:
            images = response.json()['images']
            print(f"✅ 画像一覧取得成功（{len(images)}件）")
        else:
            print("❌ 画像一覧取得失敗")
            return False
            
    else:
        print(f"❌ 画像アップロード失敗: {response.status_code}")
        print(f"   エラー: {response.text}")
        return False
    
    print("🎉 Docker環境統合テスト完了 - 全て成功!")
    return True

def test_docker_services():
    """Docker サービステスト"""
    print("🔍 Docker サービス状態確認...")
    
    # MinIO管理画面テスト
    try:
        response = requests.get("http://localhost:9001", timeout=5)
        if response.status_code == 200:
            print("✅ MinIO Console アクセス可能")
        else:
            print("❌ MinIO Console アクセス失敗")
    except:
        print("❌ MinIO Console 接続エラー")
    
    # PostgreSQL接続テスト（直接）
    print("📊 PostgreSQL接続確認...")
    # Docker composeで確認
    import subprocess
    try:
        result = subprocess.run([
            'docker', 'exec', 'image_api_postgres', 
            'psql', '-U', 'postgres', '-d', 'imagedb', '-c', 'SELECT COUNT(*) FROM image_metadata;'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ PostgreSQL直接接続成功")
        else:
            print("❌ PostgreSQL直接接続失敗")
    except:
        print("❌ PostgreSQL直接接続エラー")

if __name__ == "__main__":
    print("=" * 60)
    print("🐳 Docker環境完全統合テスト")
    print("=" * 60)
    
    success = test_full_integration()
    print()
    test_docker_services()
    
    if success:
        print("\n🎊 全テスト成功! Docker環境が正常に動作しています。")
    else:
        print("\n💥 テスト失敗。設定を確認してください。")
```

#### 統合テストの実行
```bash
# 統合テストを実行
python test_docker_integration.py
```

### トラブルシューティング

#### よくある問題と解決方法

```bash
# 1. ポート競合エラーの場合
# 個別で起動していたコンテナを停止
docker stop postgres-dev minio-dev
docker rm postgres-dev minio-dev

# 2. ビルドエラーの場合
# キャッシュをクリアして再ビルド
docker compose build --no-cache

# 3. データベース初期化の問題
# ボリュームを削除して初期化
docker compose down -v
docker compose up --build -d

# 4. メモリ不足エラーの場合
# Docker Desktop のリソース設定を確認
# Settings > Resources > Advanced でメモリを増やす

# 5. ログの詳細確認
docker compose logs --tail=50 flask_app
docker compose logs --tail=50 postgres
docker compose logs --tail=50 minio
```

---

## 📊 Step 4.5: 監視とメンテナンス

### 基本的な運用コマンド

#### アプリケーション管理
```bash
# サービス起動
docker compose up -d

# サービス停止
docker compose down

# 特定サービスの再起動
docker compose restart flask_app

# 設定変更後の再デプロイ
docker compose up --build -d

# 完全クリーンアップ（データも削除）
docker compose down -v --rmi all
```

#### ログとモニタリング
```bash
# リアルタイムログ監視
docker compose logs -f

# 特定サービスのログ
docker compose logs -f flask_app

# ディスク使用量確認
docker system df

# 未使用リソースのクリーンアップ
docker system prune -f
```

### パフォーマンス監視

#### `monitoring.py` を作成
```python
# monitoring.py - Docker環境監視スクリプト
import docker
import psutil
import time
import json

def get_container_stats():
    """コンテナリソース使用状況を取得"""
    client = docker.from_env()
    stats = {}
    
    container_names = ['image_api_flask', 'image_api_postgres', 'image_api_minio']
    
    for name in container_names:
        try:
            container = client.containers.get(name)
            if container.status == 'running':
                # CPU・メモリ使用率を取得
                stat = container.stats(stream=False)
                
                # CPU使用率計算
                cpu_delta = stat['cpu_stats']['cpu_usage']['total_usage'] - stat['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stat['cpu_stats']['system_cpu_usage'] - stat['precpu_stats']['system_cpu_usage']
                cpu_percent = (cpu_delta / system_delta) * 100.0
                
                # メモリ使用率計算
                memory_usage = stat['memory_stats']['usage']
                memory_limit = stat['memory_stats']['limit']
                memory_percent = (memory_usage / memory_limit) * 100.0
                
                stats[name] = {
                    'status': container.status,
                    'cpu_percent': round(cpu_percent, 2),
                    'memory_usage_mb': round(memory_usage / 1024 / 1024, 2),
                    'memory_percent': round(memory_percent, 2)
                }
            else:
                stats[name] = {'status': container.status}
                
        except docker.errors.NotFound:
            stats[name] = {'status': 'not_found'}
        except Exception as e:
            stats[name] = {'status': 'error', 'error': str(e)}
    
    return stats

def monitor_system():
    """システム全体の監視"""
    print("🖥️  Docker環境監視開始")
    print("=" * 60)
    
    while True:
        try:
            # システムリソース
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # コンテナ統計
            container_stats = get_container_stats()
            
            # 表示
            print(f"\n📊 システムリソース - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"CPU使用率: {cpu_percent}%")
            print(f"メモリ使用率: {memory.percent}% ({memory.used//1024//1024}MB/{memory.total//1024//1024}MB)")
            print(f"ディスク使用率: {disk.percent}%")
            
            print("\n🐳 コンテナ状況:")
            for name, stats in container_stats.items():
                if stats['status'] == 'running':
                    print(f"  {name:20} | CPU: {stats['cpu_percent']:5.1f}% | RAM: {stats['memory_usage_mb']:6.1f}MB ({stats['memory_percent']:5.1f}%)")
                else:
                    print(f"  {name:20} | Status: {stats['status']}")
            
            time.sleep(10)  # 10秒間隔で監視
            
        except KeyboardInterrupt:
            print("\n監視を終了します。")
            break
        except Exception as e:
            print(f"監視エラー: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_system()
```

---

## 🎯 Phase 4 学習成果

### ✅ 習得したスキル
- **Docker基礎**: コンテナの概念、Dockerfile作成
- **Docker Compose**: マルチコンテナ環境の構築・管理
- **環境設定**: 環境変数とシークレット管理
- **ネットワーク**: コンテナ間通信の設定
- **永続化**: ボリュームによるデータ永続化
- **監視**: ヘルスチェックとログ管理
- **セキュリティ**: 非rootユーザー、.dockerignore設定

### 🛠️ 作成したファイル
- `Dockerfile` - Flaskアプリコンテナ定義
- `docker-compose.yml` - マルチコンテナ環境定義
- `.env.example` - 環境変数テンプレート
- `.dockerignore` - Docker除外ファイル設定
- `test_docker_integration.py` - Docker統合テスト
- `monitoring.py` - Docker環境監視スクリプト

### 📈 最終システム構成
```
完成した構成:
├── Flask API アプリケーション (Dockerコンテナ)
├── PostgreSQL データベース (Dockerコンテナ)
├── MinIO オブジェクトストレージ (Dockerコンテナ)
├── Docker Compose オーケストレーション
├── 環境変数管理
├── ヘルスチェック・監視
├── 永続化ボリューム
└── 本番環境対応設定

✨ 本番デプロイ可能な状態 ✨
```

### 🚀 運用コマンドまとめ
```bash
# 🚀 環境起動
docker compose up -d

# 📊 状態確認
docker compose ps
docker compose logs -f

# 🔄 再起動
docker compose restart flask_app

# ⚠️ 停止
docker compose down

# 🧹 完全クリーンアップ
docker compose down -v --rmi all
```

### 🌐 アクセスポイント
- **API**: http://localhost:8000
- **MinIO Console**: http://localhost:9001
- **PostgreSQL**: localhost:5432

**🎊 おめでとうございます！Flask + PostgreSQL + Docker による画像メタデータ管理APIが完成しました！**

**🚀 次のステップ**: より高度な機能実装（AI画像分析、認証システム強化、クラウドデプロイなど） 