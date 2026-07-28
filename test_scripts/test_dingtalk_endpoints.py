"""
深入测试钉钉API - 寻找正确的消息获取端点
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

DINGTALK_APP_KEY = os.getenv('DINGTALK_APP_KEY', 'dingcu3gdk9wnifpzm16')
DINGTALK_APP_SECRET = os.getenv('DINGTALK_APP_SECRET', 'yn0xVpBupQxaJoBxEKuxck3k5W7gRg6gFzEail7aXFvh09KzakMoVC9m1VTtqmE5')
DINGTALK_CHAT_ID = os.getenv('DINGTALK_CHAT_ID', 'cidYDDdadQunLcx33oPumGODA==')

print("=== DingTalk API Deep Testing ===")
print(f"CHAT_ID: {DINGTALK_CHAT_ID}")
print()

# 获取token
token_response = requests.post('https://api.dingtalk.com/v1.0/oauth2/accessToken', json={
    'appKey': DINGTALK_APP_KEY,
    'appSecret': DINGTALK_APP_SECRET
}, timeout=10)

if token_response.status_code == 200:
    token_data = token_response.json()
    access_token = token_data.get('accessToken')
    print(f"Access Token: {access_token[:20]}...")
    print()

    # 测试更多可能的端点
    test_endpoints = [
        # 1. 获取企业会话列表（可能是获取群消息的入口）
        {
            'url': 'https://oapi.dingtalk.com/chat/get',
            'params': {'access_token': access_token, 'chatid': DINGTALK_CHAT_ID},
            'description': '获取群信息（基础端点）'
        },

        # 2. 尝试使用新的API格式
        {
            'url': f'https://api.dingtalk.com/v1.0/robot/group/messages/read',
            'headers': {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            'description': '机器人读取群消息（新API）'
        },

        # 3. 尝试获取群列表
        {
            'url': f'https://oapi.dingtalk.com/chat/getInfo',
            'params': {'access_token': access_token, 'chatid': DINGTALK_CHAT_ID},
            'description': '获取群详细信息'
        },

        # 4. 尝试发送消息接口（可能有列表功能）
        {
            'url': f'https://api.dingtalk.com/v1.0/robot/conversations/send',
            'headers': {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            'description': '机器人会话接口（新API）'
        },

        # 5. 尝试获取机器人所在群列表
        {
            'url': f'https://api.dingtalk.com/v1.0/org/mini/scopes',
            'headers': {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            'description': '获取组织范围（可能包含群信息）'
        },
    ]

    for endpoint in test_endpoints:
        print(f"\n{'='*60}")
        print(f"Testing: {endpoint['description']}")
        print(f"URL: {endpoint['url']}")

        try:
            if 'params' in endpoint:
                response = requests.get(endpoint['url'], params=endpoint['params'], timeout=10)
            elif 'headers' in endpoint:
                response = requests.get(endpoint['url'], headers=endpoint['headers'], timeout=10)
            else:
                response = requests.get(endpoint['url'], timeout=10)

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Response keys: {list(data.keys())}")
                    print(f"Full response: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}...")

                    if data.get('errcode') == 0 or 'data' in data or 'result' in data:
                        print("SUCCESS: This endpoint looks promising!")
                        break
                except json.JSONDecodeError:
                    print(f"Response (text): {response.text[:200]}")
            else:
                print(f"Error response: {response.text[:200]}")

        except Exception as e:
            print(f"Exception: {e}")

    # 额外测试：查看是否有chatid格式问题
    print(f"\n{'='*60}")
    print("CHAT_ID Analysis:")
    print(f"Current CHAT_ID: {DINGTALK_CHAT_ID}")
    print(f"Length: {len(DINGTALK_CHAT_ID)}")
    print(f"Starts with 'cid': {DINGTALK_CHAT_ID.startswith('cid')}")
    print(f"Contains '=': {'=' in DINGTALK_CHAT_ID}")

    # 提供一些建议
    print(f"\n{'='*60}")
    print("Suggestions:")
    print("1. Check if CHAT_ID format is correct")
    print("2. Try using OpenConversationId instead of regular chatid")
    print("3. Check if bot is actually in the group")
    print("4. Verify the permissions include message reading")

else:
    print("Failed to get access token")