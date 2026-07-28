"""
最后的尝试：从钉钉客户端获取正确的chat ID格式
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

DINGTALK_APP_KEY = os.getenv('DINGTALK_APP_KEY', 'dingcu3gdk9wnifpzm16')
DINGTALK_APP_SECRET = os.getenv('DINGTALK_APP_SECRET', 'yn0xVpBupQxaJoBxEKuxck3k5W7gRg6gFzEail7aXFvh09KzakMoVC9m1VTtqmE5')
DINGTALK_CHAT_ID = os.getenv('DINGTALK_CHAT_ID', 'cidYDDdadQunLcx33oPumGODA==')

print("=== Final Attempt: Get Correct Chat ID Format ===")
print(f"Current Conversation ID: {DINGTALK_CHAT_ID}")
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

    # 尝试通过API获取机器人所在群的正确chat ID
    # 1. 尝试获取用户的群列表
    print("=== Method 1: Get user's group list ===")
    try:
        response = requests.get(
            'https://oapi.dingtalk.com/chat/list',
            params={'access_token': access_token, 'size': 20},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")

        if response.status_code == 200:
            data = response.json()
            if data.get('errcode') == 0:
                chatlist = data.get('chatlist', [])
                print(f"Found {len(chatlist)} groups")
                for chat in chatlist[:3]:
                    print(f"  Group: {chat.get('name', 'Unknown')}")
                    print(f"    chatid: {chat.get('chatid', 'Unknown')}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. 尝试将cid转换为chat格式
    print("\n=== Method 2: CID to CHAT format conversion ===")
    # 移除"cid"前缀并添加"chat"前缀
    if DINGTALK_CHAT_ID.startswith('cid'):
        converted_chatid = 'chat' + DINGTALK_CHAT_ID[3:]
        print(f"Original CID: {DINGTALK_CHAT_ID}")
        print(f"Converted CHATID: {converted_chatid}")

        # 测试转换后的ID
        try:
            response = requests.get(
                'https://oapi.dingtalk.com/chat/get',
                params={'access_token': access_token, 'chatid': converted_chatid},
                timeout=10
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:300]}...")

            if response.status_code == 200:
                data = response.json()
                if data.get('errcode') == 0:
                    print("SUCCESS! Converted chatid works!")
        except Exception as e:
            print(f"Error: {e}")

    # 3. 尝试不带前缀的纯ID
    print("\n=== Method 3: Try ID without prefix ===")
    if DINGTALK_CHAT_ID.startswith('cid'):
        bare_id = DINGTALK_CHAT_ID[3:]
        print(f"Bare ID: {bare_id}")

        try:
            response = requests.get(
                'https://oapi.dingtalk.com/chat/get',
                params={'access_token': access_token, 'chatid': bare_id},
                timeout=10
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:300]}...")
        except Exception as e:
            print(f"Error: {e}")

    # 4. 检查是否有其他API可以获取正确格式
    print("\n=== Method 4: Alternative API approaches ===")
    alternative_apis = [
        f'https://oapi.dingtalk.com/user/getDeptUser?access_token={access_token}&deptId=1',
        f'https://oapi.dingtalk.com/user/simpleList?access_token={access_token}&departmentId=1',
    ]

    for api in alternative_apis:
        try:
            response = requests.get(api, timeout=10)
            if response.status_code == 200:
                print(f"API works: {api}")
                data = response.json()
                if data.get('errcode') == 0:
                    print(f"Success! Response: {json.dumps(data, ensure_ascii=False)[:200]}...")
                    break
        except Exception as e:
            pass

    # 5. 最后的建议
    print(f"\n{'='*60}")
    print("FINAL SUGGESTIONS:")
    print("1. The Conversation ID format (cid...) is different from Chat ID format (chat...)")
    print("2. You need to either:")
    print("   a) Get the correct Chat ID from DingTalk client group settings")
    print("   b) Use webhook instead of polling (recommended for bots)")
    print("   c) Contact DingTalk support for the correct ID format")
    print("3. Consider using DingTalk Bot Webhook API for receiving messages")

else:
    print("Failed to get access token")