from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import json
import logging
import os
from PIL import Image
import io
from werkzeug.utils import secure_filename

from .config import Config
from .auth import require_api_key
from .db import db_manager
from .s3_utils import s3_manager

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flaskアプリの初期化
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
CORS(app)

# 画像ファイルの許可拡張子
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
            img.verify()
        file_obj.seek(0)
        return True
    except Exception as e:
        logger.error(f"Invalid image file: {e}")
        return False

def analyze_image_with_gemini(file_obj):
    """Gemini APIで画像分析（オプショナル）"""
    if not Config.GEMINI_API_KEY:
        return None
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro-vision')
        
        file_obj.seek(0)
        image_data = file_obj.read()
        file_obj.seek(0)
        
        # 画像の内容を分析
        response = model.generate_content([
            "この画像について簡潔に説明してください（日本語で、100文字以内）:",
            {"mime_type": "image/jpeg", "data": image_data}
        ])
        
        return response.text if response.text else None
        
    except Exception as e:
        logger.warning(f"Gemini API analysis failed: {e}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({'status': 'healthy', 'service': 'image-metadata-api'}), 200

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
        filesize = file.tell()
        file.seek(0)  # ファイル先頭に戻る
        
        # MD5ハッシュ計算
        md5_hash = calculate_md5(file)
        
        # 重複チェック
        existing_image = db_manager.check_image_exists(md5_hash)
        if existing_image:
            return jsonify({
                'error': 'Image already exists',
                'message': 'An image with the same content already exists',
                'existing_image': existing_image
            }), 409
        
        # Gemini分析（オプショナル）
        gemini_analysis = analyze_image_with_gemini(file)
        
        # S3にアップロード
        s3_key = f"images/{md5_hash}_{original_filename}"
        s3_manager.upload_file(file, s3_key, mimetype)
        
        # データベースに保存
        saved_metadata = db_manager.save_image_metadata(
            s3_key=s3_key,
            md5_hash=md5_hash,
            original_filename=original_filename,
            mimetype=mimetype,
            filesize=filesize,
            title=metadata['title'],
            description=metadata['description'],
            gemini_analysis=gemini_analysis
        )
        
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
        
    except Exception as e:
        logger.error(f"Error in upload_image: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred while processing your request'
        }), 500

@app.errorhandler(413)
def file_too_large(error):
    """ファイルサイズ制限エラーハンドラ"""
    return jsonify({
        'error': 'File too large',
        'message': f'Maximum file size is {Config.MAX_CONTENT_LENGTH // (1024*1024)}MB'
    }), 413

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 