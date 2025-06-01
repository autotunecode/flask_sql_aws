#!/usr/bin/env python3
"""
Docker環境でのストレステスト・パフォーマンステストスクリプト
"""

import requests
import json
import io
import time
import threading
import statistics
from PIL import Image, ImageDraw, ImageFont
import random
import string
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# テスト設定
API_BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key-12345"

class StressTestSuite:
    def __init__(self):
        self.response_times = []
        self.errors = []
        self.success_count = 0
        self.total_requests = 0
        
    def create_random_image(self, width=400, height=300):
        """ランダムなテスト画像を作成"""
        # ランダムな背景色
        bg_color = (
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(100, 255)
        )
        
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # ランダムなテキスト
        random_text = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
        text_color = (
            random.randint(0, 100),
            random.randint(0, 100),
            random.randint(0, 100)
        )
        
        draw.text((20, 20), f"Stress Test: {random_text}", fill=text_color)
        draw.text((20, 50), f"Time: {time.strftime('%H:%M:%S')}", fill=text_color)
        
        # ランダムな図形
        for _ in range(random.randint(3, 8)):
            x1, y1 = random.randint(0, width-1), random.randint(0, height-1)
            x2, y2 = random.randint(0, width-1), random.randint(0, height-1)
            
            # 座標を正しい順序にする
            if x1 > x2:
                x1, x2 = x2, x1
            if y1 > y2:
                y1, y2 = y2, y1
                
            shape_color = (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )
            
            if random.choice([True, False]):
                draw.rectangle([x1, y1, x2, y2], outline=shape_color, width=2)
            else:
                draw.ellipse([x1, y1, x2, y2], outline=shape_color, width=2)
        
        # バイトストリームに保存
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=85)
        img_bytes.seek(0)
        
        return img_bytes
    
    def upload_single_image(self, test_id):
        """単一の画像アップロードテスト"""
        start_time = time.time()
        
        try:
            # テスト用画像を作成
            test_image = self.create_random_image()
            
            # メタデータを準備
            metadata = {
                "title": f"ストレステスト画像 #{test_id}",
                "description": f"ストレステスト用画像 - タイムスタンプ: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                "category": "stress_test",
                "tags": ["stress", "test", f"batch_{test_id // 10}"]
            }
            
            # リクエストデータを準備
            files = {
                'image_file': (f'stress_test_{test_id}.jpg', test_image, 'image/jpeg')
            }
            
            data = {
                'metadata': json.dumps(metadata)
            }
            
            headers = {
                'X-API-Key': API_KEY
            }
            
            response = requests.post(
                f"{API_BASE_URL}/api/upload",
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            self.total_requests += 1
            
            if response.status_code == 201:
                self.success_count += 1
                self.response_times.append(response_time)
                return {
                    'success': True,
                    'response_time': response_time,
                    'test_id': test_id,
                    'data': response.json()
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.errors.append(error_msg)
                return {
                    'success': False,
                    'response_time': response_time,
                    'test_id': test_id,
                    'error': error_msg
                }
                
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            self.total_requests += 1
            error_msg = f"Exception: {str(e)}"
            self.errors.append(error_msg)
            return {
                'success': False,
                'response_time': response_time,
                'test_id': test_id,
                'error': error_msg
            }
    
    def concurrent_upload_test(self, num_requests=20, max_workers=5):
        """並行アップロードテスト"""
        print(f"🚀 並行アップロードテスト開始")
        print(f"   - リクエスト数: {num_requests}")
        print(f"   - 最大同時実行数: {max_workers}")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.upload_single_image, i) for i in range(num_requests)]
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                result = future.result()
                if completed % 5 == 0:
                    print(f"   進行状況: {completed}/{num_requests} 完了")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"✅ 並行アップロードテスト完了")
        print(f"   - 総実行時間: {total_time:.2f}秒")
        print(f"   - 成功率: {self.success_count}/{self.total_requests} ({(self.success_count/self.total_requests)*100:.1f}%)")
        
        if self.response_times:
            print(f"   - 平均レスポンス時間: {statistics.mean(self.response_times):.3f}秒")
            print(f"   - 最短レスポンス時間: {min(self.response_times):.3f}秒")
            print(f"   - 最長レスポンス時間: {max(self.response_times):.3f}秒")
            print(f"   - 中央値レスポンス時間: {statistics.median(self.response_times):.3f}秒")
        
        if self.errors:
            print(f"   - エラー数: {len(self.errors)}")
            for error in self.errors[:3]:  # 最初の3つのエラーを表示
                print(f"     * {error}")
            if len(self.errors) > 3:
                print(f"     * ... 他 {len(self.errors) - 3} 件のエラー")
    
    def large_file_test(self):
        """大容量ファイルテスト"""
        print("📁 大容量ファイルテスト...")
        
        # 大きな画像を作成 (2MB程度)
        large_image = self.create_random_image(width=2000, height=1500)
        
        metadata = {
            "title": "大容量テスト画像",
            "description": "大容量ファイルアップロードのテスト（約2MB）",
            "category": "large_file_test",
            "tags": ["large", "performance", "test"]
        }
        
        start_time = time.time()
        
        files = {
            'image_file': ('large_test_image.jpg', large_image, 'image/jpeg')
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
                headers=headers,
                timeout=60
            )
            
            end_time = time.time()
            upload_time = end_time - start_time
            
            if response.status_code == 201:
                print(f"✅ 大容量ファイルアップロード成功")
                print(f"   - アップロード時間: {upload_time:.2f}秒")
                response_data = response.json()
                print(f"   - ファイルサイズ: {response_data['data']['filesize']} bytes")
                return True
            else:
                print(f"❌ 大容量ファイルアップロード失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 大容量ファイルアップロードエラー: {e}")
            return False
    
    def api_health_monitoring(self, duration_seconds=30, interval_seconds=2):
        """API健康状態監視テスト"""
        print(f"🏥 API健康状態監視テスト（{duration_seconds}秒間）...")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        health_checks = []
        
        while time.time() < end_time:
            check_start = time.time()
            try:
                response = requests.get(f"{API_BASE_URL}/health", timeout=5)
                check_end = time.time()
                response_time = check_end - check_start
                
                health_checks.append({
                    'timestamp': check_start,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'success': response.status_code == 200
                })
                
            except Exception as e:
                check_end = time.time()
                response_time = check_end - check_start
                health_checks.append({
                    'timestamp': check_start,
                    'response_time': response_time,
                    'status_code': None,
                    'success': False,
                    'error': str(e)
                })
            
            time.sleep(interval_seconds)
        
        # 結果分析
        successful_checks = [check for check in health_checks if check['success']]
        failed_checks = [check for check in health_checks if not check['success']]
        
        print(f"✅ 健康状態監視完了")
        print(f"   - 総チェック回数: {len(health_checks)}")
        print(f"   - 成功回数: {len(successful_checks)}")
        print(f"   - 失敗回数: {len(failed_checks)}")
        print(f"   - 成功率: {(len(successful_checks)/len(health_checks))*100:.1f}%")
        
        if successful_checks:
            response_times = [check['response_time'] for check in successful_checks]
            print(f"   - 平均レスポンス時間: {statistics.mean(response_times):.3f}秒")
            print(f"   - 最長レスポンス時間: {max(response_times):.3f}秒")
        
        return len(failed_checks) == 0

def main():
    """メインテスト実行"""
    print("🔥 Docker環境ストレステスト開始")
    print("=" * 60)
    
    stress_test = StressTestSuite()
    test_results = []
    
    # 1. 健康状態監視テスト
    print("1️⃣ API健康状態監視テスト")
    health_result = stress_test.api_health_monitoring(duration_seconds=20, interval_seconds=1)
    test_results.append(("健康状態監視", health_result))
    print()
    
    # 2. 大容量ファイルテスト
    print("2️⃣ 大容量ファイルテスト")
    large_file_result = stress_test.large_file_test()
    test_results.append(("大容量ファイル", large_file_result))
    print()
    
    # 3. 並行アップロードテスト（軽負荷）
    print("3️⃣ 並行アップロードテスト（軽負荷）")
    stress_test_light = StressTestSuite()
    stress_test_light.concurrent_upload_test(num_requests=10, max_workers=3)
    light_load_result = stress_test_light.success_count == stress_test_light.total_requests
    test_results.append(("軽負荷並行テスト", light_load_result))
    print()
    
    # 4. 並行アップロードテスト（重負荷）
    print("4️⃣ 並行アップロードテスト（重負荷）")
    stress_test_heavy = StressTestSuite()
    stress_test_heavy.concurrent_upload_test(num_requests=25, max_workers=8)
    heavy_load_result = stress_test_heavy.success_count >= stress_test_heavy.total_requests * 0.8  # 80%以上成功
    test_results.append(("重負荷並行テスト", heavy_load_result))
    print()
    
    # 結果サマリー
    print("=" * 60)
    print("📊 ストレステスト結果サマリー")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20}: {status}")
        if result:
            passed += 1
    
    print(f"\n合計: {passed}/{total} テスト通過")
    
    if passed == total:
        print("🎉 全てのストレステストが成功しました！")
        print("💪 システムは高負荷環境でも安定して動作しています。")
        return 0
    else:
        print("⚠️  一部のストレステストが失敗しました。")
        print("🔧 システムの最適化を検討してください。")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 