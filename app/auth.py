from functools import wraps
from flask import request, jsonify
from .config import Config

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
        
        if api_key != Config.API_KEY:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function 