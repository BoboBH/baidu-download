"""
测试钉钉API端点和凭证
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# 钉钉凭证
DINGTALK_APP_KEY = os.getenv('DINGTALK_APP_KEY', 'dingcu3gdk9wnifpzm16')
DINGTALK_APP_SECRET = os.getenv('DINGTALK_APP_SECRET', 'yn0xVpBupQxaJoBxEKuxck3k5W7gRg6gFzEail7aXFvh09KzakMoVC9m1VTtqmE5')
DINGTALK_CHAT_ID = os.getenv('DINGTALK_CHAT_ID', 'cidYDDdadQunLcx33oPumGODA==')

print(f"钉钉凭证:")
print(f"APP_KEY: {DINGTALK_APP_KEY}")
print(f"APP_SECRET: {DINGTALK_APP_SECRET[:20]}...")
print(f"CHAT_ID: {DINGTALK_CHAT_ID}")
print()

# 测试1: 获取access_token
print("=== 测试1: 获取access_token ===")
token_url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
token_payload = {
    "appKey": DINGTALK_APP_KEY,
    "appSecret": DINGTALK_APP_SECRET
}

try:
    token_response = requests.post(token_url, json=token_payload, timeout=10)
    print(f"Token URL: {token_url}")
    print(f"Status Code: {token_response.status_code}")
    print(f"Response: {token_response.text[:500]}")

    if token_response.status_code == 200:
        token_data = token_response.json()
        if 'accessToken' in token_data:
            access_token = token_data['accessToken']
            print(f"SUCCESS: Got access_token: {access_token[:20]}...")

            # 测试2: 尝试获取群消息
            print("\n=== TEST 2: Get group messages ===")

            # 可能的API端点
            possible_endpoints = [
                f"https://api.dingtalk.com/v1.0/conversation/messages/getList?conversationId={DINGTALK_CHAT_ID}",
                f"https://api.dingtalk.com/v1.0/group/messages/list?chatId={DINGTALK_CHAT_ID}",
                f"https://oapi.dingtalk.com/chat/get?access_token={access_token}&chatId={DINGTALK_CHAT_ID}",
                f"https://api.dingtalk.com/v1.0/message/list?conversationType=group&cid={DINGTALK_CHAT_ID}",
            ]

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            for endpoint in possible_endpoints:
                print(f"\n尝试端点: {endpoint}")
                try:
                    msg_response = requests.get(endpoint, headers=headers, timeout=10)
                    print(f"Status: {msg_response.status_code}")
                    print(f"Response: {msg_response.text[:300]}")

                    if msg_response.status_code == 200:
                        print("SUCCESS: Found valid endpoint!")
                        break
                except Exception as e:
                    print(f"ERROR: {e}")

        else:
            print(f"ERROR: No accessToken in response: {token_data}")
    else:
        print(f"ERROR: Token request failed")

except Exception as e:
    print(f"ERROR: Exception - {e}")