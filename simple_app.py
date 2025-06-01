#!/usr/bin/env python3
"""
画像・メタデータ管理API - 開発用シンプル版
データベースとMinIOなしで基本的な動作確認ができます
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import json
import logging
import os
from PIL import Image
import io
from werkzeug.utils import secure_filename
from functools import wraps

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flaskアプリの初期化
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB
CORS(app)

# 設定
API_KEY = os.getenv('API_KEY', 'test-api-key-123')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# メモリ内ストレージ（開発用）
image_storage = {}

def require_api_key(f):
    """APIキー認証デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'error': 'API key is required',
                'message': 'Please provide X-API-Key header'
            }), 401
        
        if api_key != API_KEY:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

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
            img.verify()
        file_obj.seek(0)
        return True
    except Exception as e:
        logger.error(f"Invalid image file: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        'status': 'healthy', 
        'service': 'image-metadata-api',
        'mode': 'development',
        'storage': 'memory'
    }), 200

@app.route('/api/upload', methods=['POST'])
@require_api_key
def upload_image():
    """画像・メタデータアップロードAPI（開発版）"""
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
        filesize = file.tell()
        file.seek(0)  # ファイル先頭に戻る
        
        # MD5ハッシュ計算
        md5_hash = calculate_md5(file)
        
        # 重複チェック（メモリ内）
        if md5_hash in image_storage:
            existing_image = image_storage[md5_hash]
            return jsonify({
                'error': 'Image already exists',
                'message': 'An image with the same content already exists',
                'existing_image': {
                    'id': existing_image['id'],
                    'title': existing_image['title'],
                    'description': existing_image['description']
                }
            }), 409
        
        # メモリ内ストレージに保存
        image_id = f"img_{len(image_storage) + 1}"
        saved_metadata = {
            'id': image_id,
            'md5_hash': md5_hash,
            'original_filename': original_filename,
            'mimetype': mimetype,
            'filesize': filesize,
            'title': metadata['title'],
            'description': metadata['description'],
            'storage_type': 'memory'
        }
        
        image_storage[md5_hash] = saved_metadata
        
        logger.info(f"Successfully uploaded image: {original_filename} (MD5: {md5_hash})")
        
        return jsonify({
            'message': 'Image uploaded successfully',
            'data': saved_metadata
        }), 201
        
    except Exception as e:
        logger.error(f"Error in upload_image: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred while processing your request'
        }), 500

@app.route('/api/images', methods=['GET'])
@require_api_key
def list_images():
    """保存された画像一覧を取得"""
    return jsonify({
        'message': 'Images retrieved successfully',
        'count': len(image_storage),
        'data': list(image_storage.values())
    }), 200

@app.errorhandler(413)
def file_too_large(error):
    """ファイルサイズ制限エラーハンドラ"""
    return jsonify({
        'error': 'File too large',
        'message': f'Maximum file size is {app.config["MAX_CONTENT_LENGTH"] // (1024*1024)}MB'
    }), 413

if __name__ == '__main__':
    print("=== 画像・メタデータ管理API - 開発版 ===")
    print(f"API Key: {API_KEY}")
    print("ヘルスチェック: http://localhost:5000/health")
    print("アップロード: POST http://localhost:5000/api/upload")
    print("画像一覧: GET http://localhost:5000/api/images")
    print("=====================================")
    app.run(host='0.0.0.0', port=5000, debug=True) 