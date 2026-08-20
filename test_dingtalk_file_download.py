"""
钉钉文件下载测试脚本
测试使用downloadCode下载钉钉文件
"""
import os
import sys
import requests
import json
from pathlib import Path

# 修复Windows编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dingtalk_stream import Credential
from src.config.settings import Settings
from src.utils.logger import get_logger

# 设置日志
logger = get_logger(__name__)

# 下载目录设置
DOWNLOAD_DIR = Path("d:/temp/dingtalk_downloads")

def test_dingtalk_file_download():
    """测试钉钉文件下载功能"""

    print("=" * 80)
    print("[TEST] DingTalk File Download Test")
    print("=" * 80)

    try:
        # 1. 加载配置
        print("[INFO] Loading configuration...")
        settings = Settings()

        dingtalk_app_key = settings.dingtalk_app_key
        dingtalk_app_secret = settings.dingtalk_app_secret

        print(f"   [OK] App Key: {dingtalk_app_key[:10]}..." if dingtalk_app_key else "   [ERROR] App Key: Not configured")
        print(f"   [OK] App Secret: {dingtalk_app_secret[:10]}..." if dingtalk_app_secret else "   [ERROR] App Secret: Not configured")

        if not dingtalk_app_key or not dingtalk_app_secret:
            print("[ERROR] DingTalk configuration missing, please check DINGTALK_APP_KEY and DINGTALK_APP_SECRET in .env file")
            return False

        # 2. 创建凭证
        print("\n[INFO] Creating DingTalk credential...")
        credential = Credential(dingtalk_app_key, dingtalk_app_secret)
        print("   [OK] Credential created successfully")

        # 3. 使用你提供的测试数据
        print("\n[INFO] Test message data:")
        test_message_data = {
            'senderPlatform': 'Win',
            'openThreadId': 'cidCdq7DXpNepxSGvjYesVuY7VbY3/CBS6JB+KFBTlbe+4=',
            'content': {
                'spaceId': '29431333271',
                'fileName': '中信银行AI部署架构.md',
                'downloadCode': 'u+4l19FUsDqB3gBbl8UYg2vJ+afs5OlTKld7M+eiWLyRZa67olZOvFStW2asEBCf5K1fTwi9IE7pDHtKEShcYIUcfPC6b18YQSXEIvF3tMjykQZD6EDp2PFYMekO0UWNUjhW230VCo9Phe5eZYgFdls1bgfZZdsWEWZlxQdsHaBWUWm3jZKZWkO6qWdnDt4bm0vlqu1Up9WThXcNdMYXASv9EqklPHCKc/VOYYKLIcc=',
                'fileId': '232941987026'
            }
        }

        file_name = test_message_data['content']['fileName']
        download_code = test_message_data['content']['downloadCode']
        file_id = test_message_data['content']['fileId']
        space_id = test_message_data['content']['spaceId']

        print(f"   [FILE] Filename: {file_name}")
        print(f"   [CODE] Download code: {download_code[:20]}...")
        print(f"   [ID] File ID: {file_id}")
        print(f"   [SPACE] Space ID: {space_id}")

        # 4. 方法1: 尝试直接使用downloadCode下载（钉钉媒体下载API）
        print("\n[METHOD 1] Testing DingTalk media download API...")

        # 方法1: 尝试使用downloadCode直接下载
        print("   [DIRECT] Trying direct download with downloadCode...")

        # 尝试不同的钉钉下载API
        download_attempts = [
            # 方法1: 钉钉媒体下载API
            {
                'name': 'Media Download API v1.0',
                'url': f"https://api.dingtalk.com/v1.0/media/download?downloadCode={download_code}",
                'method': 'GET'
            },
            # 方法2: 钉钉媒体下载API v2
            {
                'name': 'Media Download API v2.0',
                'url': f"https://api.dingtalk.com/v2.0/media/download?downloadCode={download_code}",
                'method': 'GET'
            },
            # 方法3: 直接使用downloadCode作为文件路径
            {
                'name': 'Direct downloadCode approach',
                'url': f"https://api.dingtalk.com/media/download?downloadCode={download_code}",
                'method': 'GET'
            }
        ]

        for attempt in download_attempts:
            print(f"   [TRY] Trying: {attempt['name']}")
            print(f"   [URL] {attempt['url'][:60]}...")

            try:
                if attempt['method'] == 'GET':
                    response = requests.get(attempt['url'], stream=True, timeout=30)
                else:
                    response = requests.post(attempt['url'], stream=True, timeout=30)

                print(f"   [STATUS] Response: {response.status_code}")

                if response.status_code == 200:
                    print(f"   [SUCCESS] Download successful!")
                    break
                elif response.status_code == 302:
                    # 重定向
                    redirect_url = response.headers.get('Location', '')
                    if redirect_url:
                        print(f"   [REDIRECT] Following redirect to: {redirect_url[:60]}...")
                        response = requests.get(redirect_url, stream=True, timeout=30)
                        if response.status_code == 200:
                            print(f"   [SUCCESS] Download successful after redirect!")
                            break
                else:
                    print(f"   [FAIL] {response.text[:200]}")
            except Exception as e:
                print(f"   [ERROR] {str(e)[:100]}")
                continue

        # 如果所有方法都失败，尝试获取token后重试
        if response.status_code != 200:
            print("   [TOKEN] All direct methods failed, trying with authentication...")

            # 尝试不同的token获取方法
            token_attempts = [
                {
                    'name': 'GetToken v1.0',
                    'url': "https://api.dingtalk.com/v1.0/oauth2/getAccessToken"
                },
                {
                    'name': 'GetToken v2.0',
                    'url': "https://api.dingtalk.com/v2.0/oauth2/getAccessToken"
                },
                {
                    'name': 'GetToken Old API',
                    'url': "https://oapi.dingtalk.com/gettoken"
                }
            ]

            access_token = None
            for token_attempt in token_attempts:
                print(f"   [TOKEN] Trying: {token_attempt['name']}")

                try:
                    if 'getAccessToken' in token_attempt['url']:
                        token_data = {
                            "appKey": dingtalk_app_key,
                            "appSecret": dingtalk_app_secret
                        }
                        token_response = requests.post(token_attempt['url'], json=token_data, timeout=10)
                    else:
                        # 旧版API使用GET请求
                        params = {
                            "appkey": dingtalk_app_key,
                            "appsecret": dingtalk_app_secret
                        }
                        token_response = requests.get(token_attempt['url'], params=params, timeout=10)

                    token_result = token_response.json()
                    print(f"   [TOKEN] Response: {json.dumps(token_result, indent=2, ensure_ascii=False)[:200]}...")

                    if 'accessToken' in token_result:
                        access_token = token_result['accessToken']
                        print(f"   [SUCCESS] Token obtained: {access_token[:20]}...")
                        break
                    elif 'access_token' in token_result:
                        access_token = token_result['access_token']
                        print(f"   [SUCCESS] Token obtained: {access_token[:20]}...")
                        break

                except Exception as e:
                    print(f"   [ERROR] {str(e)[:100]}")
                    continue

            if not access_token:
                print("   [ERROR] Failed to obtain access token from all methods")
                return False

            # 使用token重试下载
            print("   [RETRY] Retrying download with access token...")

            headers = {
                'x-acs-dingtalk-access-token': access_token,
                'Authorization': f'Bearer {access_token}',
                'User-Agent': 'DingTalk-File-Downloader/1.0'
            }

            response = requests.get(f"https://api.dingtalk.com/v1.0/media/download?downloadCode={download_code}",
                                  headers=headers, stream=True, timeout=30)
            print(f"   [STATUS] Response with token: {response.status_code}")

        print(f"   [STATUS] Response status: {response.status_code}")
        print(f"   [HEADERS] Response headers: {dict(response.headers)}")

        if response.status_code == 200:
            # 创建下载目录
            download_dir = DOWNLOAD_DIR
            download_dir.mkdir(parents=True, exist_ok=True)

            # 保存文件
            file_path = download_dir / file_name
            print(f"   [SAVE] Saving file to: {file_path}")

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = file_path.stat().st_size
            print(f"   [SUCCESS] File downloaded successfully!")
            print(f"   [SIZE] File size: {file_size:,} bytes ({file_size/1024:.2f} KB)")

            # 验证文件内容
            if file_size > 0:
                print(f"   [VERIFY] File content verification passed")

                # 如果是文本文件，显示前几行
                if file_name.endswith(('.md', '.txt', '.json')):
                    print(f"   [PREVIEW] File content preview:")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[:5]
                        for line in lines:
                            print(f"      {line.rstrip()}")

                return True
            else:
                print(f"   [ERROR] File is empty")
                return False

        else:
            print(f"   [ERROR] Download failed")
            print(f"   [RESPONSE] Response content: {response.text[:500]}")

            # 5. 方法2: 尝试使用钉钉开放平台API
            print("\n[METHOD 2] Testing DingTalk open platform file download API...")

            # 获取access_token
            print("   [TOKEN] Getting Access Token...")
            token_url = "https://api.dingtalk.com/v1.0/oauth2/getAccessToken"
            token_data = {
                "appKey": dingtalk_app_key,
                "appSecret": dingtalk_app_secret
            }

            token_response = requests.post(token_url, json=token_data)
            token_result = token_response.json()

            print(f"   [TOKEN] Token response: {json.dumps(token_result, indent=2, ensure_ascii=False)}")

            if 'accessToken' in token_result:
                access_token = token_result['accessToken']
                print(f"   [TOKEN] Access Token obtained successfully: {access_token[:20]}...")

                # 尝试使用另一种下载方式
                file_download_url = f"https://api.dingtalk.com/v1.0/media/files/{file_id}/download"

                download_headers = {
                    'x-acs-dingtalk-access-token': access_token,
                    'Authorization': f'Bearer {access_token}'
                }

                print(f"   [TRY] Trying file download API: {file_download_url}")
                download_response = requests.get(file_download_url, headers=download_headers, stream=True)

                print(f"   [STATUS] Response status: {download_response.status_code}")

                if download_response.status_code == 200:
                    print(f"   [SUCCESS] Found working download method!")
                    print(f"   [HEADERS] Response headers: {dict(download_response.headers)}")
                    return True
                else:
                    print(f"   [ERROR] Download failed: {download_response.text[:500]}")
            else:
                print(f"   [ERROR] Failed to get Access Token")

            return False

    except Exception as e:
        print(f"[ERROR] Exception occurred during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("[START] Starting DingTalk file download test")
    print("=" * 80)

    success = test_dingtalk_file_download()

    print("\n" + "=" * 80)
    if success:
        print("[SUCCESS] File download test completed successfully!")
        print(f"[INFO] Test files saved in: {DOWNLOAD_DIR}/")
    else:
        print("[FAILED] File download test failed")
        print("[TIPS] Please check:")
        print("   1. DingTalk configuration in .env file is correct")
        print("   2. Network connection is normal")
        print("   3. DingTalk app has sufficient permissions")
        print("   4. downloadCode has not expired")
    print("=" * 80)

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())