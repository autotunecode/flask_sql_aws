# 📊 Phase 2: PostgreSQL統合

## PostgreSQLとは？
**PostgreSQL**は高性能なオープンソースのリレーショナルデータベース管理システム（RDBMS）です。ACIDトランザクション、複雑なクエリ、拡張性に優れ、企業レベルのアプリケーションで広く使用されています。

---

## 🎯 Phase 2の学習目標
- PostgreSQLの基本概念を理解
- Pythonからのデータベース接続方法を習得
- テーブル設計とSQL操作を実装
- データベース初期化スクリプトの作成

---

## 🛠️ Step 2.1: PostgreSQLローカル環境構築

### Windows環境でのPostgreSQL準備

#### オプション1: PostgreSQL直接インストール
```bash
# PostgreSQLをダウンロード・インストール
# https://www.postgresql.org/download/windows/
# インストール時にパスワードを設定（例: password）
```

#### オプション2: Docker使用（推奨）
```bash
# PostgreSQLをDockerで起動（簡単）
docker run --name postgres-dev \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=imagedb \
  -p 5432:5432 \
  -d postgres:15-alpine
```

### 🧪 接続テスト
```bash
# Docker版の場合
docker exec -it postgres-dev psql -U postgres -d imagedb

# 直接インストール版の場合
psql -U postgres -d imagedb
```

---

## 📋 Step 2.2: データベース設計

### テーブル構造の設計

画像メタデータ管理システムに必要なテーブルを設計します：

```sql
-- 画像メタデータテーブル
CREATE TABLE image_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    s3_key VARCHAR(500) NOT NULL,              -- S3オブジェクトキー
    md5_hash VARCHAR(32) NOT NULL UNIQUE,      -- MD5ハッシュ（重複防止）
    original_filename VARCHAR(255) NOT NULL,   -- 元のファイル名
    mimetype VARCHAR(100) NOT NULL,            -- MIMEタイプ
    filesize BIGINT NOT NULL,                  -- ファイルサイズ（bytes）
    title VARCHAR(200) NOT NULL,               -- タイトル
    description TEXT,                          -- 説明
    gemini_analysis TEXT,                      -- Gemini分析結果
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成（検索性能向上）
CREATE INDEX idx_image_metadata_md5_hash ON image_metadata(md5_hash);
CREATE INDEX idx_image_metadata_created_at ON image_metadata(created_at DESC);
CREATE INDEX idx_image_metadata_title ON image_metadata(title);
```

**🎓 学習ポイント**:
- `UUID`: 一意識別子（Globally Unique Identifier）
- `UNIQUE制約`: データの一意性を保証
- `インデックス`: 検索性能の最適化
- `TIMESTAMP`: 日時データの管理

### 初期化スクリプトの作成

#### `init_db.sql` を作成
```sql
-- init_db.sql - データベース初期化スクリプト
-- PostgreSQL 15以上で動作

-- データベースが存在しない場合は作成（Docker環境では自動作成される）
-- CREATE DATABASE imagedb;

-- 拡張機能の有効化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- UUID生成機能

-- 既存テーブルがあれば削除（開発環境のみ）
DROP TABLE IF EXISTS image_metadata CASCADE;

-- 画像メタデータテーブル作成
CREATE TABLE image_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    s3_key VARCHAR(500) NOT NULL,
    md5_hash VARCHAR(32) NOT NULL UNIQUE,
    original_filename VARCHAR(255) NOT NULL,
    mimetype VARCHAR(100) NOT NULL,
    filesize BIGINT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    gemini_analysis TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX idx_image_metadata_md5_hash ON image_metadata(md5_hash);
CREATE INDEX idx_image_metadata_created_at ON image_metadata(created_at DESC);
CREATE INDEX idx_image_metadata_title ON image_metadata(title);

-- 更新日時自動更新のトリガー作成
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_image_metadata_updated_at 
    BEFORE UPDATE ON image_metadata 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- 動作確認用のサンプルデータ挿入
INSERT INTO image_metadata (
    s3_key, md5_hash, original_filename, mimetype, filesize, title, description
) VALUES (
    'samples/sample.jpg',
    'abcdef1234567890abcdef1234567890',
    'sample.jpg',
    'image/jpeg',
    1024576,
    'サンプル画像',
    'データベース動作確認用のサンプル画像です。'
);

-- 確認クエリ
SELECT 
    id,
    original_filename,
    title,
    filesize,
    created_at
FROM image_metadata;
```

#### 初期化スクリプトの実行
```bash
# Dockerの場合
docker exec -i postgres-dev psql -U postgres -d imagedb < init_db.sql

# 直接インストールの場合
psql -U postgres -d imagedb -f init_db.sql
```

---

## 🐍 Step 2.3: Python-PostgreSQL統合

### データベース接続クラスの実装

#### `app/db.py` を作成
```python
# app/db.py - データベース操作クラス
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
import logging
from .config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """PostgreSQLデータベース管理クラス"""
    
    def __init__(self):
        self.connection = None
        self._connect()
    
    def _connect(self):
        """データベースに接続"""
        try:
            self.connection = psycopg2.connect(
                host=Config.DB_HOST,
                database=Config.POSTGRES_DB,
                user=Config.POSTGRES_USER,
                password=Config.POSTGRES_PASSWORD,
                port=5432,
                cursor_factory=RealDictCursor  # 辞書形式で結果を取得
            )
            self.connection.autocommit = False  # 手動コミット
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def check_connection(self):
        """接続状態をチェック"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.warning(f"Database connection check failed: {e}")
            self._connect()  # 再接続を試行
            return False
    
    def save_image_metadata(self, s3_key, md5_hash, original_filename, 
                          mimetype, filesize, title, description, gemini_analysis=None):
        """画像メタデータを保存"""
        try:
            with self.connection.cursor() as cursor:
                insert_query = """
                INSERT INTO image_metadata (
                    s3_key, md5_hash, original_filename, mimetype, 
                    filesize, title, description, gemini_analysis
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at;
                """
                
                cursor.execute(insert_query, (
                    s3_key, md5_hash, original_filename, mimetype,
                    filesize, title, description, gemini_analysis
                ))
                
                result = cursor.fetchone()
                self.connection.commit()
                
                # 保存されたデータを返す
                return {
                    'id': str(result['id']),
                    's3_key': s3_key,
                    'md5_hash': md5_hash,
                    'original_filename': original_filename,
                    'mimetype': mimetype,
                    'filesize': filesize,
                    'title': title,
                    'description': description,
                    'gemini_analysis': gemini_analysis,
                    'created_at': result['created_at'].isoformat()
                }
                
        except psycopg2.IntegrityError as e:
            self.connection.rollback()
            if 'unique constraint' in str(e).lower():
                logger.warning(f"Duplicate image detected: {md5_hash}")
                raise ValueError("Image with same content already exists")
            raise
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error saving image metadata: {e}")
            raise
    
    def check_image_exists(self, md5_hash):
        """MD5ハッシュで画像の存在をチェック"""
        try:
            with self.connection.cursor() as cursor:
                select_query = """
                SELECT id, s3_key, original_filename, title, created_at
                FROM image_metadata 
                WHERE md5_hash = %s;
                """
                
                cursor.execute(select_query, (md5_hash,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        'id': str(result['id']),
                        's3_key': result['s3_key'],
                        'original_filename': result['original_filename'],
                        'title': result['title'],
                        'created_at': result['created_at'].isoformat()
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error checking image existence: {e}")
            raise
    
    def get_image_list(self, limit=50, offset=0):
        """画像一覧を取得"""
        try:
            with self.connection.cursor() as cursor:
                select_query = """
                SELECT id, s3_key, original_filename, title, description,
                       filesize, created_at
                FROM image_metadata 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s;
                """
                
                cursor.execute(select_query, (limit, offset))
                results = cursor.fetchall()
                
                return [
                    {
                        'id': str(row['id']),
                        's3_key': row['s3_key'],
                        'original_filename': row['original_filename'],
                        'title': row['title'],
                        'description': row['description'],
                        'filesize': row['filesize'],
                        'created_at': row['created_at'].isoformat()
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"Error fetching image list: {e}")
            raise
    
    def close(self):
        """データベース接続を閉じる"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

# グローバルなデータベースマネージャーインスタンス
db_manager = DatabaseManager()
```

**🎓 学習ポイント**:
- `psycopg2`: Python-PostgreSQL接続ライブラリ
- `RealDictCursor`: 結果を辞書形式で取得
- `autocommit=False`: トランザクション手動管理
- `try-except`: エラーハンドリング
- `rollback()`: トランザクションのロールバック
- `RETURNING`: INSERT後にデータを取得

### 🧪 Step 2.4: データベース機能のテスト

#### `test_database.py` を作成
```python
# test_database.py - データベース機能テスト
from app.db import db_manager
import time

def test_database_operations():
    """データベース操作のテスト"""
    print("🗄️ データベース操作テスト開始")
    
    # 1. 接続テスト
    print("1. 接続テスト...")
    if db_manager.check_connection():
        print("✅ データベース接続成功")
    else:
        print("❌ データベース接続失敗")
        return
    
    # 2. データ保存テスト
    print("2. データ保存テスト...")
    try:
        test_data = db_manager.save_image_metadata(
            s3_key="test/test_image.jpg",
            md5_hash=f"test_hash_{int(time.time())}",  # 一意性のため時刻を追加
            original_filename="test_image.jpg",
            mimetype="image/jpeg",
            filesize=1024,
            title="テスト画像",
            description="データベーステスト用画像です。"
        )
        print("✅ データ保存成功")
        print(f"   ID: {test_data['id']}")
        print(f"   作成日時: {test_data['created_at']}")
    except Exception as e:
        print(f"❌ データ保存失敗: {e}")
        return
    
    # 3. 重複チェックテスト
    print("3. 重複チェックテスト...")
    try:
        existing = db_manager.check_image_exists(test_data['md5_hash'])
        if existing:
            print("✅ 重複チェック成功")
            print(f"   既存画像タイトル: {existing['title']}")
        else:
            print("❌ 重複チェック失敗")
    except Exception as e:
        print(f"❌ 重複チェックエラー: {e}")
    
    # 4. 一覧取得テスト
    print("4. 一覧取得テスト...")
    try:
        image_list = db_manager.get_image_list(limit=5)
        print(f"✅ 一覧取得成功（{len(image_list)}件）")
        for img in image_list[:2]:  # 最初の2件を表示
            print(f"   - {img['title']} ({img['filesize']} bytes)")
    except Exception as e:
        print(f"❌ 一覧取得失敗: {e}")
    
    print("🎉 データベーステスト完了")

if __name__ == "__main__":
    test_database_operations()
```

#### テストの実行
```bash
# PostgreSQLが起動していることを確認
docker ps  # postgres-devコンテナが起動中か確認

# テストを実行
python test_database.py
```

### 📊 Step 2.5: FlaskアプリにDB機能を統合

#### `app/app.py` を更新
```python
# app/app.py の先頭部分に追加
from .db import db_manager

# 新しいエンドポイントを追加
@app.route('/api/images', methods=['GET'])
@require_api_key
def get_images():
    """画像一覧取得API"""
    try:
        # クエリパラメータの取得
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        # パラメータ検証
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 1
        if offset < 0:
            offset = 0
        
        # データベースから画像一覧を取得
        images = db_manager.get_image_list(limit=limit, offset=offset)
        
        return jsonify({
            'images': images,
            'count': len(images),
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_images: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to retrieve images'
        }), 500

@app.route('/api/database/status', methods=['GET'])
@require_api_key  
def database_status():
    """データベース状態確認API"""
    try:
        if db_manager.check_connection():
            return jsonify({
                'status': 'connected',
                'database': Config.POSTGRES_DB,
                'host': Config.DB_HOST
            }), 200
        else:
            return jsonify({
                'status': 'disconnected',
                'message': 'Database connection failed'
            }), 503
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
```

#### API動作確認
```bash
# アプリケーション起動
python -m app.app

# データベース状態確認
curl -H "X-API-Key: test-api-key-12345" http://localhost:5000/api/database/status

# 画像一覧取得
curl -H "X-API-Key: test-api-key-12345" http://localhost:5000/api/images
```

---

## 🎯 Phase 2 学習成果

### ✅ 習得したスキル
- **PostgreSQL基礎**: データベース、テーブル、インデックス
- **SQL操作**: CREATE, INSERT, SELECT, UPDATE
- **Python-DB統合**: psycopg2によるデータベース接続
- **トランザクション**: コミット、ロールバック
- **エラーハンドリング**: データベースエラーの適切な処理
- **API統合**: FlaskアプリにDB機能を統合

### 🛠️ 作成したファイル
- `init_db.sql` - データベース初期化スクリプト
- `app/db.py` - データベース操作クラス
- `test_database.py` - データベーステストスクリプト
- 更新された `app/app.py` - DB統合API

### 📈 システム現状
```
現在の構成:
├── Flask API アプリケーション
├── PostgreSQL データベース
├── 基本的なCRUD操作
└── API認証機能

次のフェーズ:
└── ファイルアップロード機能（MinIO統合）
```

**🚀 次のステップ**: [Phase 3: ファイルアップロード](./PHASE3_FILE_UPLOAD.md) 