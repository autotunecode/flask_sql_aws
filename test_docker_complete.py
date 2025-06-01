#!/usr/bin/env python3
"""
Docker環境での完全版APIテストスクリプト
"""

import requests
import json
import io
from PIL import Image, ImageDraw
import os
import sys

# テスト設定
API_BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key-12345"

def create_test_image():
    """テスト用の画像を作成"""
    img = Image.new('RGB', (300, 200), color='lightblue')
    draw = ImageDraw.Draw(img)
    
    # テキストを描画
    draw.text((50, 50), "Docker Test Image", fill='darkblue')
    draw.text((50, 80), "Flask + PostgreSQL + MinIO", fill='darkgreen')
    draw.text((50, 110), "Complete Integration Test", fill='red')
    
    # 円を描画
    draw.ellipse([200, 50, 280, 130], outline='orange', width=3)
    
    # バイトストリームに保存
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes

def test_health_check():
    """ヘルスチェックテスト"""
    print("🏥 ヘルスチェックテスト...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print("✅ ヘルスチェック成功")
            print(f"   レスポンス: {response.json()}")
            return True
        else:
            print(f"❌ ヘルスチェック失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ヘルスチェックエラー: {e}")
        return False

def test_upload_image():
    """画像アップロードテスト"""
    print("📤 画像アップロードテスト...")
    
    # テスト用画像を作成
    test_image = create_test_image()
    
    # メタデータを準備
    metadata = {
        "title": "Docker環境テスト画像",
        "description": "Flask + PostgreSQL + MinIO統合テスト用のサンプル画像です。",
        "category": "test",
        "tags": ["docker", "flask", "postgresql", "minio", "test"]
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
        response = requests.post(
            f"{API_BASE_URL}/api/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if response.status_code == 201:
            print("✅ 画像アップロード成功")
            response_data = response.json()
            print(f"   画像ID: {response_data['data']['id']}")
            print(f"   ファイル名: {response_data['data']['original_filename']}")
            print(f"   MD5ハッシュ: {response_data['data']['md5_hash']}")
            print(f"   S3キー: {response_data['data']['s3_key']}")
            if 'download_url' in response_data['data']:
                print(f"   ダウンロードURL: {response_data['data']['download_url'][:50]}...")
            if response_data['data'].get('gemini_analysis'):
                print(f"   Gemini分析: {response_data['data']['gemini_analysis']}")
            return response_data['data']
        else:
            print(f"❌ 画像アップロード失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 画像アップロードエラー: {e}")
        return None

def test_duplicate_upload():
    """重複アップロードテスト"""
    print("🔄 重複アップロードテスト...")
    
    # 同じ画像を再度アップロード
    test_image = create_test_image()
    
    metadata = {
        "title": "重複テスト画像",
        "description": "重複チェックのテスト"
    }
    
    files = {
        'image_file': ('duplicate_test.jpg', test_image, 'image/jpeg')
    }
    
    data = {
        'metadata': json.dumps(metadata)
    }
    
    headers = {
        'X-API-Key': API_KEY
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if response.status_code == 409:
            print("✅ 重複チェック成功（期待される動作）")
            print(f"   メッセージ: {response.json()['message']}")
            return True
        else:
            print(f"❌ 重複チェック失敗: {response.status_code}")
            print(f"   レスポンス: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 重複チェックエラー: {e}")
        return False

def test_invalid_api_key():
    """無効なAPIキーテスト"""
    print("🔑 無効なAPIキーテスト...")
    
    test_image = create_test_image()
    
    metadata = {
        "title": "テスト",
        "description": "テスト"
    }
    
    files = {
        'image_file': ('test.jpg', test_image, 'image/jpeg')
    }
    
    data = {
        'metadata': json.dumps(metadata)
    }
    
    headers = {
        'X-API-Key': 'invalid-key'
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if response.status_code == 401:
            print("✅ APIキー認証成功（期待される動作）")
            return True
        else:
            print(f"❌ APIキー認証失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ APIキー認証エラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🐳 Docker環境完全版APIテスト開始")
    print("=" * 50)
    
    test_results = []
    
    # 各テストを実行
    test_results.append(("ヘルスチェック", test_health_check()))
    test_results.append(("画像アップロード", test_upload_image() is not None))
    test_results.append(("重複チェック", test_duplicate_upload()))
    test_results.append(("APIキー認証", test_invalid_api_key()))
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print("📊 テスト結果サマリー")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20}: {status}")
        if result:
            passed += 1
    
    print(f"\n合計: {passed}/{total} テスト通過")
    
    if passed == total:
        print("🎉 全てのテストが成功しました！")
        return 0
    else:
        print("⚠️  一部のテストが失敗しました。")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 