"""
测试钉钉新版API（使用Conversation ID）
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

DINGTALK_APP_KEY = os.getenv('DINGTALK_APP_KEY', 'dingcu3gdk9wnifpzm16')
DINGTALK_APP_SECRET = os.getenv('DINGTALK_APP_SECRET', 'yn0xVpBupQxaJoBxEKuxck3k5W7gRg6gFzEail7aXFvh09KzakMoVC9m1VTtqmE5')
DINGTALK_CHAT_ID = os.getenv('DINGTALK_CHAT_ID', 'cidYDDdadQunLcx33oPumGODA==')

print("=== Testing Modern DingTalk API with Conversation ID ===")
print(f"Conversation ID: {DINGTALK_CHAT_ID}")
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

    # 测试新版API端点（支持Conversation ID）
    modern_endpoints = [
        # 1. 获取会话消息（新版API）
        {
            'url': 'https://api.dingtalk.com/v1.0/conversation/messages/getList',
            'params': {
                'conversationId': DINGTALK_CHAT_ID,
                'conversationType': 'group',
                'pageSize': 10
            },
            'headers': {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            'method': 'GET',
            'description': '获取会话消息列表（新版API）'
        },

        # 2. 获取会话信息
        {
            'url': 'https://api.dingtalk.com/v1.0/conversations/get',
            'params': {
                'conversationId': DINGTALK_CHAT_ID
            },
            'headers': {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            'method': 'GET',
            'description': '获取会话信息（新版API）'
        },

        # 3. 发送消息到会话
        {
            'url': 'https://api.dingtalk.com/v1.0/robot/group/messages/send',
            'params': {},
            'data': {
                'msgParam': {'content': 'test message'},
                'msg': {'msgtype': 'text'},
                'conversationId': DINGTALK_CHAT_ID
            },
            'headers': {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            'method': 'POST',
            'description': '发送群消息（测试连接）'
        },

        # 4. 获取机器人所在的群列表
        {
            'url': 'https://api.dingtalk.com/v1.0/bot/group/list',
            'params': {
                'size': 20
            },
            'headers': {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            'method': 'GET',
            'description': '获取机器人所在的群列表（新版API）'
        },
    ]

    for endpoint in modern_endpoints:
        print(f"\n{'='*60}")
        print(f"Testing: {endpoint['description']}")
        print(f"URL: {endpoint['url']}")
        print(f"Method: {endpoint['method']}")

        try:
            if endpoint['method'] == 'GET':
                if 'data' in endpoint:
                    # 有些GET请求可能需要在body中传递参数
                    response = requests.get(
                        endpoint['url'],
                        params=endpoint.get('params', {}),
                        headers=endpoint['headers'],
                        timeout=10
                    )
                else:
                    response = requests.get(
                        endpoint['url'],
                        params=endpoint.get('params', {}),
                        headers=endpoint['headers'],
                        timeout=10
                    )
            else:  # POST
                if 'data' in endpoint:
                    response = requests.post(
                        endpoint['url'],
                        params=endpoint.get('params', {}),
                        json=endpoint['data'],
                        headers=endpoint['headers'],
                        timeout=10
                    )
                else:
                    response = requests.post(
                        endpoint['url'],
                        params=endpoint.get('params', {}),
                        headers=endpoint['headers'],
                        timeout=10
                    )

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Response keys: {list(data.keys())}")
                    print(f"Response: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}...")

                    # 检查是否成功
                    if 'data' in data or data.get('code') == 'Success' or data.get('errcode') == 0:
                        print("SUCCESS! This endpoint works!")
                        break
                except json.JSONDecodeError:
                    print(f"Response (text): {response.text[:200]}")
            else:
                print(f"Error response: {response.text[:200]}")

        except Exception as e:
            print(f"Exception: {e}")

    # 如果所有方法都失败，提供替代方案
    print(f"\n{'='*60}")
    print("ALTERNATIVE SOLUTION:")
    print("如果所有API方法都失败，可以考虑使用钉钉机器人Webhook方式")
    print("1. 在群聊中添加机器人时设置Webhook URL")
    print("2. 机器人会主动推送新消息到Webhook")
    print("3. 不需要主动获取消息历史")

else:
    print("Failed to get access token")