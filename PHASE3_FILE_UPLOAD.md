# 📤 Phase 3: ファイルアップロード機能

## MinIOとは？
**MinIO**は高性能なオブジェクトストレージサーバーで、Amazon S3と完全互換のAPIを提供します。画像、動画、ドキュメントなどの非構造化データの保存に適しており、開発環境から本番環境まで幅広く使用されています。

---

## 🎯 Phase 3の学習目標
- オブジェクトストレージの概念を理解
- MinIOの設定と操作方法を習得
- ファイルアップロード機能の実装
- 画像処理とバリデーションの実装
- S3互換APIの使用方法を習得

---

## 🛠️ Step 3.1: MinIOローカル環境構築

### MinIOサーバーの起動

#### Dockerを使用したMinIO起動
```bash
# MinIOコンテナを起動
docker run -d \
  --name minio-dev \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -v minio_data:/data \
  minio/minio server /data --console-address ":9001"
```

#### MinIO動作確認
```bash
# MinIOコンテナの状態確認
docker ps | grep minio

# MinIO管理画面にアクセス
# ブラウザで http://localhost:9001 を開く
# ユーザー名: minioadmin
# パスワード: minioadmin
```

**🎓 学習ポイント**:
- **ポート9000**: MinIO API（S3互換API）
- **ポート9001**: MinIO Console（Web管理画面）
- **バケット**: S3のコンテナ概念（フォルダのようなもの）

---

## 🔧 Step 3.2: S3クライアント実装

### boto3を使用したS3操作クラス

#### `app/s3_utils.py` を作成
```python
# app/s3_utils.py - S3/MinIO操作クラス
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging
import time
from .config import Config

logger = logging.getLogger(__name__)

class S3Manager:
    """S3/MinIO管理クラス"""
    
    def __init__(self):
        self.s3_client = None
        self._init_s3_client()
    
    def _init_s3_client(self):
        """S3/MinIOクライアントを初期化"""
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=Config.MINIO_ENDPOINT_URL,
                aws_access_key_id=Config.MINIO_ACCESS_KEY,
                aws_secret_access_key=Config.MINIO_SECRET_KEY,
                region_name='us-east-1'  # MinIOでは任意のリージョン
            )
            
            # バケットが存在するかチェック、なければ作成（リトライ付き）
            self._ensure_bucket_exists()
            logger.info("S3 client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def _ensure_bucket_exists(self):
        """バケットの存在を確認し、なければ作成（競合状態を適切に処理）"""
        max_retries = 5
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # まずバケットの存在確認
                self.s3_client.head_bucket(Bucket=Config.MINIO_BUCKET_NAME)
                logger.info(f"Bucket {Config.MINIO_BUCKET_NAME} already exists")
                return
                
            except ClientError as e:
                error_code = int(e.response['Error']['Code'])
                if error_code == 404:
                    # バケットが存在しない場合は作成を試行
                    try:
                        self.s3_client.create_bucket(Bucket=Config.MINIO_BUCKET_NAME)
                        logger.info(f"Created bucket {Config.MINIO_BUCKET_NAME}")
                        return
                        
                    except ClientError as create_error:
                        error_code = create_error.response.get('Error', {}).get('Code', '')
                        
                        if error_code in ['BucketAlreadyExists', 'BucketAlreadyOwnedByYou']:
                            # バケットが既に存在する場合は正常とみなす
                            logger.info(f"Bucket {Config.MINIO_BUCKET_NAME} already exists (created by another process)")
                            return
                        else:
                            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to create bucket: {create_error}")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay)
                                retry_delay *= 2  # 指数バックオフ
                            else:
                                logger.error(f"Failed to create bucket after {max_retries} attempts")
                                raise
                else:
                    logger.error(f"Error checking bucket: {e}")
                    raise
    
    def upload_file(self, file_obj, s3_key, content_type):
        """ファイルをS3/MinIOにアップロード"""
        try:
            self.s3_client.upload_fileobj(
                file_obj,
                Config.MINIO_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'uploaded_by': 'image_api'
                    }
                }
            )
            
            logger.info(f"Successfully uploaded file to {s3_key}")
            return True
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"Error uploading file to S3: {e}")
            raise
    
    def get_file_url(self, s3_key, expiration=3600):
        """S3オブジェクトのプリサインドURLを生成"""
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': Config.MINIO_BUCKET_NAME, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return response
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
    
    def delete_file(self, s3_key):
        """S3からファイルを削除"""
        try:
            self.s3_client.delete_object(
                Bucket=Config.MINIO_BUCKET_NAME,
                Key=s3_key
            )
            logger.info(f"Successfully deleted file: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file from S3: {e}")
            raise
    
    def list_files(self, prefix="", max_keys=100):
        """バケット内のファイル一覧を取得"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=Config.MINIO_BUCKET_NAME,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat()
                    })
            
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise

# グローバルなS3マネージャーインスタンス
s3_manager = S3Manager()
```

**🎓 学習ポイント**:
- `boto3`: AWS SDK for Python（S3互換APIクライアント）
- `endpoint_url`: MinIOのAPIエンドポイント指定
- `upload_fileobj()`: ファイルオブジェクトの直接アップロード
- `generate_presigned_url()`: 時間制限付きダウンロードURL生成
- 指数バックオフ: エラー発生時の再試行間隔を段階的に増加

---

## 🖼️ Step 3.3: 画像処理機能の実装

### 画像バリデーションとメタデータ抽出

#### `app/image_utils.py` を作成
```python
# app/image_utils.py - 画像処理ユーティリティ
import hashlib
import io
import logging
from PIL import Image, ExifTags
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# 許可される画像ファイル拡張子
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    """ファイル拡張子が許可されているかチェック"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_md5(file_obj):
    """ファイルのMD5ハッシュを計算"""
    hash_md5 = hashlib.md5()
    file_obj.seek(0)
    for chunk in iter(lambda: file_obj.read(4096), b""):
        hash_md5.update(chunk)
    file_obj.seek(0)
    return hash_md5.hexdigest()

def validate_image(file_obj):
    """画像ファイルのバリデーション"""
    try:
        file_obj.seek(0)
        with Image.open(file_obj) as img:
            # 画像が正常に開けるかチェック
            img.verify()
        file_obj.seek(0)
        return True
    except Exception as e:
        logger.error(f"Invalid image file: {e}")
        return False

def get_image_info(file_obj):
    """画像の詳細情報を取得"""
    try:
        file_obj.seek(0)
        with Image.open(file_obj) as img:
            info = {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,  # (width, height)
                'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
            }
            
            # EXIF情報の取得（JPEGの場合）
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif = {}
                for tag, value in img._getexif().items():
                    if tag in ExifTags.TAGS:
                        exif[ExifTags.TAGS[tag]] = value
                info['exif'] = exif
            
        file_obj.seek(0)
        return info
    except Exception as e:
        logger.error(f"Error getting image info: {e}")
        file_obj.seek(0)
        return None

def resize_image_if_needed(file_obj, max_width=2048, max_height=2048, quality=85):
    """画像が大きすぎる場合はリサイズ"""
    try:
        file_obj.seek(0)
        with Image.open(file_obj) as img:
            original_size = img.size
            
            # リサイズが必要かチェック
            if img.width <= max_width and img.height <= max_height:
                file_obj.seek(0)
                return file_obj, False  # リサイズ不要
            
            # アスペクト比を保持してリサイズ
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # 新しいファイルオブジェクトに保存
            output = io.BytesIO()
            
            # 形式を保持（RGBAをJPEGで保存する場合はRGBに変換）
            if img.mode == 'RGBA' and img.format == 'JPEG':
                # 白背景で合成
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])  # アルファチャンネルをマスクとして使用
                img = background
            
            # 保存
            save_format = img.format if img.format else 'JPEG'
            img.save(output, format=save_format, quality=quality, optimize=True)
            output.seek(0)
            
            logger.info(f"Image resized from {original_size} to {img.size}")
            return output, True
            
    except Exception as e:
        logger.error(f"Error resizing image: {e}")
        file_obj.seek(0)
        return file_obj, False

def create_thumbnail(file_obj, size=(300, 300)):
    """サムネイル画像を作成"""
    try:
        file_obj.seek(0)
        with Image.open(file_obj) as img:
            # アスペクト比を保持してサムネイル作成
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # サムネイルを新しいファイルオブジェクトに保存
            thumbnail = io.BytesIO()
            
            # 形式の調整
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            
            img.save(thumbnail, format='JPEG', quality=80, optimize=True)
            thumbnail.seek(0)
            
        file_obj.seek(0)
        return thumbnail
        
    except Exception as e:
        logger.error(f"Error creating thumbnail: {e}")
        file_obj.seek(0)
        return None
```

**🎓 学習ポイント**:
- `PIL (Pillow)`: Python画像処理ライブラリ
- `verify()`: 画像ファイルの整合性チェック
- `thumbnail()`: アスペクト比を保持したリサイズ
- `EXIF`: 画像の撮影情報メタデータ
- `io.BytesIO()`: メモリ上でのファイル操作

---

## 📤 Step 3.4: ファイルアップロードAPI実装

### アップロードエンドポイントの作成

#### `app/app.py` にアップロード機能を追加
```python
# app/app.py の先頭にインポート追加
import hashlib
import json
import io
from werkzeug.utils import secure_filename

from .s3_utils import s3_manager
from .image_utils import (
    allowed_file, calculate_md5, validate_image, 
    get_image_info, resize_image_if_needed
)

@app.route('/api/upload', methods=['POST'])
@require_api_key
def upload_image():
    """画像・メタデータアップロードAPI"""
    try:
        # リクエスト検証
        if 'image_file' not in request.files:
            return jsonify({
                'error': 'No image file provided',
                'message': 'Please provide an image file with key "image_file"'
            }), 400
        
        if 'metadata' not in request.form:
            return jsonify({
                'error': 'No metadata provided',
                'message': 'Please provide metadata as JSON string with key "metadata"'
            }), 400
        
        # ファイル取得と検証
        file = request.files['image_file']
        if file.filename == '':
            return jsonify({
                'error': 'No file selected',
                'message': 'Please select a file to upload'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'Invalid file type',
                'message': f'Allowed file types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # 画像バリデーション
        if not validate_image(file):
            return jsonify({
                'error': 'Invalid image file',
                'message': 'The uploaded file is not a valid image'
            }), 400
        
        # メタデータ解析
        try:
            metadata = json.loads(request.form['metadata'])
        except json.JSONDecodeError:
            return jsonify({
                'error': 'Invalid metadata format',
                'message': 'Metadata must be valid JSON'
            }), 400
        
        # 必須フィールドチェック
        if 'title' not in metadata or 'description' not in metadata:
            return jsonify({
                'error': 'Missing required metadata',
                'message': 'Metadata must contain "title" and "description"'
            }), 400
        
        # ファイル情報取得
        original_filename = secure_filename(file.filename)
        mimetype = file.content_type or 'application/octet-stream'
        file.seek(0, 2)  # ファイル末尾に移動
        original_filesize = file.tell()
        file.seek(0)  # ファイル先頭に戻る
        
        # 画像情報取得
        image_info = get_image_info(file)
        
        # 大きな画像の場合はリサイズ
        processed_file, was_resized = resize_image_if_needed(file, max_width=2048, max_height=2048)
        
        # 処理後のファイルサイズを取得
        processed_file.seek(0, 2)
        processed_filesize = processed_file.tell()
        processed_file.seek(0)
        
        # MD5ハッシュ計算（処理後のファイルで）
        md5_hash = calculate_md5(processed_file)
        
        # 重複チェック
        existing_image = db_manager.check_image_exists(md5_hash)
        if existing_image:
            return jsonify({
                'error': 'Image already exists',
                'message': 'An image with the same content already exists',
                'existing_image': existing_image
            }), 409
        
        # S3にアップロード
        s3_key = f"images/{md5_hash}_{original_filename}"
        s3_manager.upload_file(processed_file, s3_key, mimetype)
        
        # データベースに保存
        saved_metadata = db_manager.save_image_metadata(
            s3_key=s3_key,
            md5_hash=md5_hash,
            original_filename=original_filename,
            mimetype=mimetype,
            filesize=processed_filesize,
            title=metadata['title'],
            description=metadata['description'],
            gemini_analysis=None  # 後で実装
        )
        
        # レスポンス用追加情報
        saved_metadata.update({
            'was_resized': was_resized,
            'original_filesize': original_filesize,
            'processed_filesize': processed_filesize,
            'image_info': image_info
        })
        
        # プリサインドURL生成
        try:
            download_url = s3_manager.get_file_url(s3_key)
            saved_metadata['download_url'] = download_url
        except Exception as e:
            logger.warning(f"Failed to generate download URL: {e}")
        
        logger.info(f"Successfully uploaded image: {original_filename} (MD5: {md5_hash})")
        
        return jsonify({
            'message': 'Image uploaded successfully',
            'data': saved_metadata
        }), 201
        
    except ValueError as e:
        # 重複画像などのビジネスロジックエラー
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 409
    except Exception as e:
        logger.error(f"Error in upload_image: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred while processing your request'
        }), 500

@app.route('/api/files', methods=['GET'])
@require_api_key
def list_files():
    """S3ファイル一覧取得API"""
    try:
        prefix = request.args.get('prefix', 'images/')
        max_keys = min(int(request.args.get('limit', 50)), 100)
        
        files = s3_manager.list_files(prefix=prefix, max_keys=max_keys)
        
        return jsonify({
            'files': files,
            'count': len(files),
            'prefix': prefix
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to list files'
        }), 500
```

---

## 🧪 Step 3.5: アップロード機能のテスト

### テストスクリプトの作成

#### `test_upload.py` を作成
```python
# test_upload.py - ファイルアップロード機能テスト
import requests
import json
import io
from PIL import Image, ImageDraw

# テスト設定
API_BASE_URL = "http://localhost:5000"
API_KEY = "test-api-key-12345"

def create_test_image():
    """テスト用画像を作成"""
    img = Image.new('RGB', (800, 600), color='lightblue')
    draw = ImageDraw.Draw(img)
    
    # テキストと図形を描画
    draw.text((50, 50), "Test Image", fill='darkblue')
    draw.text((50, 80), "Flask Upload Test", fill='darkgreen')
    draw.rectangle([100, 150, 300, 350], outline='red', width=3)
    draw.ellipse([400, 150, 600, 350], outline='orange', width=3)
    
    # バイトストリームに保存
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes

def test_upload_api():
    """アップロードAPIのテスト"""
    print("📤 アップロードAPIテスト開始")
    
    # テスト用画像を作成
    test_image = create_test_image()
    
    # メタデータを準備
    metadata = {
        "title": "テスト画像1",
        "description": "アップロード機能のテスト用画像です。Flask + MinIO統合テスト。",
        "category": "test",
        "tags": ["test", "upload", "flask", "minio"]
    }
    
    # リクエストデータを準備
    files = {
        'image_file': ('test_image.jpg', test_image, 'image/jpeg')
    }
    
    data = {
        'metadata': json.dumps(metadata)
    }
    
    headers = {
        'X-API-Key': API_KEY
    }
    
    try:
        print("1. 画像アップロードテスト...")
        response = requests.post(
            f"{API_BASE_URL}/api/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if response.status_code == 201:
            print("✅ アップロード成功")
            response_data = response.json()
            print(f"   画像ID: {response_data['data']['id']}")
            print(f"   S3キー: {response_data['data']['s3_key']}")
            print(f"   MD5ハッシュ: {response_data['data']['md5_hash']}")
            if response_data['data'].get('was_resized'):
                print(f"   リサイズ実行: {response_data['data']['original_filesize']} -> {response_data['data']['processed_filesize']} bytes")
            if 'download_url' in response_data['data']:
                print(f"   ダウンロードURL: {response_data['data']['download_url'][:50]}...")
            
            # 重複アップロードテスト
            print("2. 重複アップロードテスト...")
            test_image.seek(0)  # ファイルポインタをリセット
            files_dup = {
                'image_file': ('test_image_duplicate.jpg', test_image, 'image/jpeg')
            }
            
            response_dup = requests.post(
                f"{API_BASE_URL}/api/upload",
                files=files_dup,
                data=data,
                headers=headers
            )
            
            if response_dup.status_code == 409:
                print("✅ 重複チェック成功（期待される動作）")
            else:
                print(f"❌ 重複チェック失敗: {response_dup.status_code}")
            
        else:
            print(f"❌ アップロード失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")

def test_file_list_api():
    """ファイル一覧APIのテスト"""
    print("📋 ファイル一覧APIテスト...")
    
    headers = {'X-API-Key': API_KEY}
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/files", headers=headers)
        
        if response.status_code == 200:
            print("✅ ファイル一覧取得成功")
            response_data = response.json()
            print(f"   ファイル数: {response_data['count']}")
            
            for file_info in response_data['files'][:3]:  # 最初の3ファイルを表示
                print(f"   - {file_info['key']} ({file_info['size']} bytes)")
        else:
            print(f"❌ ファイル一覧取得失敗: {response.status_code}")
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")

def test_invalid_cases():
    """エラーケースのテスト"""
    print("🚫 エラーケーステスト...")
    
    headers = {'X-API-Key': API_KEY}
    
    # 1. ファイルなしテスト
    response = requests.post(f"{API_BASE_URL}/api/upload", headers=headers)
    if response.status_code == 400:
        print("✅ ファイルなしエラー処理成功")
    
    # 2. 無効なAPIキーテスト
    invalid_headers = {'X-API-Key': 'invalid-key'}
    response = requests.post(f"{API_BASE_URL}/api/upload", headers=invalid_headers)
    if response.status_code == 401:
        print("✅ 無効APIキーエラー処理成功")
    
    print("🎉 全テスト完了")

if __name__ == "__main__":
    # MinIOとPostgreSQLが起動していることを確認
    print("🔍 前提条件確認...")
    print("- MinIOコンテナが起動していることを確認: docker ps | grep minio")
    print("- PostgreSQLコンテナが起動していることを確認: docker ps | grep postgres")
    print()
    
    test_upload_api()
    print()
    test_file_list_api()
    print()
    test_invalid_cases()
```

#### テストの実行
```bash
# 必要なサービスが起動していることを確認
docker ps

# Flaskアプリケーション起動（別ターミナル）
python -m app.app

# テスト実行
python test_upload.py
```

### MinIO管理画面での確認
```bash
# ブラウザでMinIO Console にアクセス
# http://localhost:9001
# ユーザー名: minioadmin
# パスワード: minioadmin

# imagesバケット内でアップロードされたファイルを確認
```

---

## 🎯 Phase 3 学習成果

### ✅ 習得したスキル
- **オブジェクトストレージ**: MinIOの概念と操作
- **S3互換API**: boto3を使用したファイル操作
- **ファイルアップロード**: Flaskでのマルチパートフォーム処理
- **画像処理**: Pillowを使用した画像操作・バリデーション
- **セキュリティ**: ファイルタイプ検証、サイズ制限
- **エラーハンドリング**: ファイル操作の例外処理

### 🛠️ 作成したファイル
- `app/s3_utils.py` - S3/MinIO操作クラス
- `app/image_utils.py` - 画像処理ユーティリティ
- 更新された `app/app.py` - アップロードAPI
- `test_upload.py` - アップロード機能テストスクリプト

### 📈 システム現状
```
現在の構成:
├── Flask API アプリケーション
├── PostgreSQL データベース
├── MinIO オブジェクトストレージ  ← 新規追加
├── 画像アップロード機能        ← 新規追加
├── 画像処理・バリデーション     ← 新規追加
└── API認証機能

次のフェーズ:
└── Docker化（環境統一・本番対応）
```

**🚀 次のステップ**: [Phase 4: Docker化](./PHASE4_DOCKER.md) 