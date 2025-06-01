# 🚀 Flask + PostgreSQL + Docker 完全ガイド
## 画像メタデータ管理API開発ハンズオン

### 📋 目次
1. [プロジェクト概要](#プロジェクト概要)
2. [学習目標](#学習目標)
3. [環境準備](#環境準備)
4. [Phase 1: Flask基礎](#phase-1-flask基礎)
5. [Phase 2: PostgreSQL統合](#phase-2-postgresql統合)
6. [Phase 3: ファイルアップロード](#phase-3-ファイルアップロード)
7. [Phase 4: Docker化](#phase-4-docker化)
8. [Phase 5: テスト実装](#phase-5-テスト実装)
9. [本番環境への展開](#本番環境への展開)

---

## 📖 プロジェクト概要

このチュートリアルでは、**画像メタデータ管理API**を構築しながら、モダンなWebアプリケーション開発の基礎を学習します。

### 🎯 構築するシステム
- **画像アップロード機能**: 画像ファイルをS3互換ストレージに保存
- **メタデータ管理**: タイトル、説明、タグなどの情報をPostgreSQLに保存
- **重複検出**: MD5ハッシュによる重複画像の検出
- **API認証**: APIキーによるセキュア認証
- **REST API**: 標準的なHTTP APIの提供

### 🛠️ 技術スタック
| 技術 | 役割 | 学習ポイント |
|------|------|-------------|
| **Flask** | Webフレームワーク | REST API、ルーティング、リクエスト処理 |
| **PostgreSQL** | データベース | SQL、テーブル設計、データ永続化 |
| **MinIO** | オブジェクトストレージ | S3互換API、ファイル管理 |
| **Docker** | コンテナ化 | 環境統一、デプロイ、オーケストレーション |
| **Gunicorn** | WSGIサーバー | 本番環境対応、パフォーマンス |

---

## 🎯 学習目標

このチュートリアル完了後、以下のスキルを習得できます：

### Flask
- ✅ Flaskアプリケーションの基本構造
- ✅ ルーティングとHTTPメソッド
- ✅ リクエスト/レスポンス処理
- ✅ ファイルアップロード処理
- ✅ エラーハンドリング
- ✅ アプリケーション設定管理

### PostgreSQL
- ✅ データベース設計とテーブル作成
- ✅ Python-PostgreSQL接続（psycopg2）
- ✅ CRUDオペレーション
- ✅ トランザクション管理
- ✅ データベースマイグレーション

### Docker
- ✅ Dockerfileの作成
- ✅ Docker Composeによるマルチコンテナ環境
- ✅ 環境変数管理
- ✅ ボリュームとネットワーク
- ✅ ヘルスチェック設定

---

## 💻 環境準備

### 前提条件
- Python 3.9以上がインストールされている
- Gitがインストールされている
- テキストエディタ（VS Code推奨）

### Windows環境での準備

#### 1. Python仮想環境の作成
```bash
# プロジェクトディレクトリを作成
mkdir flask-image-api
cd flask-image-api

# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
venv\Scripts\activate

# 最新のpipにアップグレード
python -m pip install --upgrade pip
```

#### 2. 基本パッケージのインストール
```bash
# 基本パッケージをインストール
pip install flask flask-cors psycopg2-binary pillow boto3 python-dotenv requests gunicorn
```

#### 3. Docker Desktopのインストール
1. [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)をダウンロード
2. インストーラーを実行し、指示に従ってインストール
3. コンピューターを再起動
4. Docker Desktopを起動

#### 4. インストール確認
```bash
# Pythonバージョン確認
python --version

# Dockerバージョン確認
docker --version
docker compose --version
```

---

## 📚 Phase 1: Flask基礎

### Flask とは？
**Flask**は軽量なPython製Webフレームワークです。シンプルな構造で、小〜中規模のWebアプリケーション開発に適しています。

### 🔰 Step 1.1: 最初のFlaskアプリケーション

プロジェクトの基本構造を作成しましょう：

```
flask-image-api/
├── app/
│   ├── __init__.py
│   ├── app.py          # メインアプリケーション
│   ├── config.py       # 設定管理
│   └── auth.py         # 認証機能
├── requirements.txt    # 依存関係
├── .env               # 環境変数
└── README.md
```

#### `app/__init__.py` を作成
```python
# app/__init__.py - Pythonパッケージとして認識させるファイル
```

#### `app/config.py` を作成
```python
# app/config.py - アプリケーション設定を管理
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """アプリケーション設定クラス"""
    
    # Flask設定
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # データベース設定
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'imagedb')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
    
    # S3/MinIO設定
    MINIO_ENDPOINT_URL = os.getenv('MINIO_ENDPOINT_URL', 'http://localhost:9000')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
    MINIO_BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME', 'images')
    
    # API設定
    API_KEY = os.getenv('API_KEY', 'your-secret-api-key')
    
    # Gemini API（オプション）
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
```

**🎓 学習ポイント**:
- `os.getenv()`: 環境変数から設定を取得
- `dotenv`: .envファイルから環境変数を読み込み
- クラス設定パターン: 設定を整理して管理

#### `app/auth.py` を作成
```python
# app/auth.py - API認証機能
from functools import wraps
from flask import request, jsonify
from .config import Config

def require_api_key(f):
    """API認証デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # リクエストヘッダーからAPIキーを取得
        api_key = request.headers.get('X-API-Key')
        
        # APIキーの検証
        if not api_key or api_key != Config.API_KEY:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Valid API key required'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function
```

**🎓 学習ポイント**:
- `@wraps`: デコレータの実装パターン
- `request.headers`: HTTPヘッダーの取得
- `jsonify()`: JSON形式のレスポンス作成

#### `app/app.py` を作成
```python
# app/app.py - メインアプリケーション
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

from .config import Config
from .auth import require_api_key

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flaskアプリの初期化
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
CORS(app)  # CORS（Cross-Origin Resource Sharing）を有効化

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        'status': 'healthy',
        'service': 'image-metadata-api',
        'version': '1.0.0'
    }), 200

@app.route('/api/info', methods=['GET'])
@require_api_key
def api_info():
    """API情報エンドポイント（認証必要）"""
    return jsonify({
        'name': 'Image Metadata API',
        'version': '1.0.0',
        'description': 'Flask + PostgreSQL + MinIO による画像メタデータ管理API',
        'endpoints': {
            'GET /health': 'ヘルスチェック',
            'GET /api/info': 'API情報（認証必要）',
            'POST /api/upload': '画像アップロード（認証必要）'
        }
    }), 200

@app.errorhandler(413)
def file_too_large(error):
    """ファイルサイズ制限エラーハンドラ"""
    return jsonify({
        'error': 'File too large',
        'message': f'Maximum file size is {Config.MAX_CONTENT_LENGTH // (1024*1024)}MB'
    }), 413

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

**🎓 学習ポイント**:
- `Flask(__name__)`: アプリケーションインスタンスの作成
- `@app.route()`: URLルーティングの定義
- `methods=['GET', 'POST']`: HTTPメソッドの指定
- `@app.errorhandler()`: エラーハンドリング
- `CORS`: 異なるドメインからのアクセスを許可

### 🧪 Step 1.2: 最初のテスト

#### `.env` ファイルを作成
```bash
# .env - 環境変数設定
API_KEY=test-api-key-12345
SECRET_KEY=your-secret-key-here
POSTGRES_PASSWORD=your-secure-password
```

#### `requirements.txt` を作成
```
Flask==2.3.3
Flask-CORS==4.0.0
psycopg2-binary==2.9.7
boto3==1.28.57
Pillow==10.0.1
python-dotenv==1.0.0
gunicorn==21.2.0
requests==2.32.3
```

#### アプリケーションの実行
```bash
# 依存関係をインストール
pip install -r requirements.txt

# アプリケーションを起動
python -m app.app
```

#### 動作確認
```bash
# ヘルスチェック（認証不要）
curl http://localhost:5000/health

# API情報（認証必要）
curl -H "X-API-Key: test-api-key-12345" http://localhost:5000/api/info
```

**🎓 学習成果**:
- ✅ Flaskアプリケーションの基本構造を理解
- ✅ ルーティングとHTTPメソッドを実装
- ✅ 環境変数による設定管理を実装
- ✅ API認証機能を実装

---

このチュートリアルはPhase 2以降も続きます。次のフェーズではPostgreSQLとの統合を学習します。

**💡 重要**: このフェーズで作成したファイルは、後のフェーズでも使用します。必ず保存してください。

**🚀 次のステップ**: [Phase 2: PostgreSQL統合](./PHASE2_POSTGRESQL.md) 