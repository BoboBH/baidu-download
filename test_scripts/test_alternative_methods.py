"""
测试钉钉API的不同调用方法
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

DINGTALK_APP_KEY = os.getenv('DINGTALK_APP_KEY', 'dingcu3gdk9wnifpzm16')
DINGTALK_APP_SECRET = os.getenv('DINGTALK_APP_SECRET', 'yn0xVpBupQxaJoBxEKuxck3k5W7gRg6gFzEail7aXFvh09KzakMoVC9m1VTtqmE5')
DINGTALK_CHAT_ID = os.getenv('DINGTALK_CHAT_ID', 'cidYDDdadQunLcx33oPumGODA==')

print("=== Alternative DingTalk API Methods ===")
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

    # 方法1: 尝试使用POST而不是GET
    print("=== Method 1: POST instead of GET ===")
    try:
        response = requests.post(
            'https://oapi.dingtalk.com/chat/get',
            params={'access_token': access_token, 'chatid': DINGTALK_CHAT_ID},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

    # 方法2: 尝试使用JSON body而不是URL参数
    print("\n=== Method 2: JSON body instead of URL params ===")
    try:
        response = requests.post(
            f'https://oapi.dingtalk.com/chat/get?access_token={access_token}',
            json={'chatid': DINGTALK_CHAT_ID},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

    # 方法3: 尝试不同的参数格式
    print("\n=== Method 3: Different parameter formats ===")
    param_formats = [
        {'chatid': DINGTALK_CHAT_ID},
        {'conversationId': DINGTALK_CHAT_ID},
        {'cid': DINGTALK_CHAT_ID.replace('cid', '')},
        {'chat_id': DINGTALK_CHAT_ID},
        {'chatId': DINGTALK_CHAT_ID},
    ]

    for params in param_formats:
        try:
            response = requests.get(
                'https://oapi.dingtalk.com/chat/get',
                params={'access_token': access_token, **params},
                timeout=10
            )
            print(f"Params: {params}")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:100]}...")

            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('errcode') == 0:
                        print("SUCCESS! This parameter format works!")
                        break
                except:
                    pass
        except Exception as e:
            print(f"Error: {e}")
        print()

    # 方法4: 尝试使用机器人接收消息的webhook替代方案
    print("\n=== Method 4: Check webhook alternatives ===")
    webhook_endpoints = [
        'https://oapi.dingtalk.com/robot/send?access_token={token}',
        'https://oapi.dingtalk.com/robot/message/send?access_token={token}',
    ]

    for endpoint_template in webhook_endpoints:
        url = endpoint_template.format(token=access_token)
        print(f"Webhook endpoint: {url}")

    # 方法5: 尝试获取机器人的群列表
    print("\n=== Method 5: Get bot's group list ===")
    list_endpoints = [
        f'https://oapi.dingtalk.com/chat/list?access_token={access_token}&size=10',
        f'https://api.dingtalk.com/v1.0/robot/group/groups?access_token={access_token}',
    ]

    for endpoint in list_endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            print(f"Endpoint: {endpoint}")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")

            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('errcode') == 0 and 'chatlist' in data:
                        print("SUCCESS! Found groups the bot is in:")
                        for group in data['chatlist'][:3]:
                            print(f"  - {group.get('name', 'Unknown')}: {group.get('chatid', 'Unknown')}")
                        break
                except:
                    pass
        except Exception as e:
            print(f"Error: {e}")

else:
    print("Failed to get access token")