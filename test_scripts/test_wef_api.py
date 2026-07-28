"""
wewe-rss API 测试脚本
测试能否获取微信公众号文章数据
"""
import requests
import json
from datetime import datetime

class WefRssTester:
    """wewe-rss API测试器"""

    def __init__(self, base_url="http://localhost:4000"):
        self.base_url = base_url
        self.session = requests.Session()

    def test_connection(self):
        """测试基础连接"""
        try:
            print(f"=== Testing Connection: {self.base_url} ===")
            response = self.session.get(f"{self.base_url}/")
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                print("[OK] Connection successful!")
                return True
            else:
                print(f"[FAIL] Connection failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"[ERROR] Connection exception: {e}")
            return False

    def discover_endpoints(self):
        """发现可用的API端点"""
        common_endpoints = [
            "/api/accounts",
            "/api/articles",
            "/api/posts",
            "/api/feeds",
            "/api/wechat",
            "/dash",
            "/api",
            "/rss"
        ]

        print("\n=== Testing Common Endpoints ===")
        for endpoint in common_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    print(f"[OK] {endpoint} - Available")
                    try:
                        data = response.json()
                        print(f"   Return Type: JSON")
                        if isinstance(data, dict) and 'data' in data:
                            print(f"   Data Keys: {list(data.keys())}")
                    except:
                        print(f"   Return Type: HTML")
                elif response.status_code == 404:
                    print(f"[NO] {endpoint} - Not Found")
                else:
                    print(f"[WARN] {endpoint} - Status: {response.status_code}")
            except Exception as e:
                print(f"[ERROR] {endpoint} - Error: {e}")

    def test_api_structure(self):
        """测试API结构"""
        print("\n=== Testing API Structure ===")

        # 尝试获取账号列表
        test_endpoints = [
            {"endpoint": "/api/accounts", "method": "GET"},
            {"endpoint": "/api/articles", "method": "GET"},
            {"endpoint": "/api/posts", "method": "GET"},
            {"endpoint": "/api/feeds", "method": "GET"},
        ]

        for api in test_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{api['endpoint']}", timeout=10)
                print(f"\n[REQUEST] {api['endpoint']} [{api['method']}]")
                print(f"   Status: {response.status_code}")

                if response.status_code == 200:
                    print(f"   [OK] Success")
                    try:
                        data = response.json()
                        print(f"   Data Type: {type(data)}")

                        if isinstance(data, dict):
                            print(f"   Data Keys: {list(data.keys())}")
                            if 'data' in data:
                                items = data['data']
                                if isinstance(items, list):
                                    print(f"   Data Items: {len(items)}")
                                    if len(items) > 0:
                                        print(f"   First Item Keys: {list(items[0].keys())}")
                                elif isinstance(items, dict):
                                    print(f"   Data Type: dict")
                                    print(f"   Data Keys: {list(items.keys())}")
                        elif isinstance(data, list):
                            print(f"   List Data, Items: {len(data)}")
                            if len(data) > 0:
                                print(f"   First Item Keys: {list(data[0].keys())}")
                        else:
                            print(f"   Raw Data")

                    except json.JSONDecodeError:
                        print(f"   HTML Response")
                        # 显示部分HTML内容
                        content = response.text[:200]
                        print(f"   Content Preview: {content}...")

                elif response.status_code == 404:
                    print(f"   [NO] Endpoint Not Found")
                else:
                    print(f"   [WARN] Other Status Code")

            except Exception as e:
                print(f"   [ERROR] Request Exception: {e}")

def main():
    """主测试函数"""
    print("=" * 60)
    print("wefe-rss API Test")
    print("=" * 60)

    # 创建测试器
    tester = WefRssTester("http://localhost:4000")

    # 测试连接
    if not tester.test_connection():
        print("\n[WARN] Cannot connect to wewe-rss, please ensure service is running")
        return

    # 发现端点
    tester.discover_endpoints()

    # 测试API结构
    tester.test_api_structure()

    print("\n" + "=" * 60)
    print("Test Completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
