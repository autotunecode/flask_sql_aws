#!/usr/bin/env python3
"""
画像・メタデータ管理APIの基本テストスクリプト
"""

import os
import sys
import requests
import json

# テスト用の環境変数設定
os.environ['DB_HOST'] = 'localhost'
os.environ['POSTGRES_DB'] = 'imagedb'
os.environ['POSTGRES_USER'] = 'postgres'
os.environ['POSTGRES_PASSWORD'] = 'password'
os.environ['MINIO_ENDPOINT_URL'] = 'http://localhost:9000'
os.environ['MINIO_ACCESS_KEY'] = 'minioadmin'
os.environ['MINIO_SECRET_KEY'] = 'minioadmin'
os.environ['MINIO_BUCKET_NAME'] = 'images'
os.environ['API_KEY'] = 'test-api-key-123'

def test_health_endpoint():
    """ヘルスチェックエンドポイントのテスト"""
    try:
        response = requests.get('http://localhost:5000/health')
        print(f"ヘルスチェック: {response.status_code}")
        print(f"レスポンス: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"ヘルスチェックエラー: {e}")
        return False

def test_upload_without_auth():
    """認証なしでのアップロードテスト（401エラーを期待）"""
    try:
        response = requests.post('http://localhost:5000/api/upload')
        print(f"認証なしアップロード: {response.status_code}")
        print(f"レスポンス: {response.json()}")
        return response.status_code == 401
    except Exception as e:
        print(f"認証なしアップロードエラー: {e}")
        return False

def main():
    """メインテスト関数"""
    print("=== 画像・メタデータ管理API テスト ===")
    
    # Flaskアプリが起動しているかチェック
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        print("✓ Flaskアプリケーションが起動しています")
    except requests.exceptions.ConnectionError:
        print("✗ Flaskアプリケーションが起動していません")
        print("先にFlaskアプリを起動してください: python -m flask run")
        return False
    except Exception as e:
        print(f"✗ 接続エラー: {e}")
        return False
    
    # テスト実行
    tests = [
        ("ヘルスチェック", test_health_endpoint),
        ("認証なしアップロード", test_upload_without_auth),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            print(f"✓ {test_name} 成功")
            passed += 1
        else:
            print(f"✗ {test_name} 失敗")
    
    print(f"\n=== テスト結果: {passed}/{total} 成功 ===")
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 