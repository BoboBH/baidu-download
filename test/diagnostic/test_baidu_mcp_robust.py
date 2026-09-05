#!/usr/bin/env python3
import requests
import json
import time
import sys

# Configuration
AUTH_TOKEN = "123.e4ecb1648bd7452260db272f4465448b.Y7DN7-4DoSGomdNHW_qvUfnKPqnZJBkrU2F8ZLw.ihRBUQ"
BASE_URL = "https://mcp-pan.baidu.com"

def test_baidu_mcp():
    """Test Baidu Pan MCP Server"""
    print("Testing Baidu Pan MCP Server")
    print("=" * 50)

    # Test 1: Check if we can reach the SSE endpoint
    print("\n1. Testing SSE endpoint accessibility...")
    try:
        response = requests.get(
            f"{BASE_URL}/sse",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=5
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Length: {len(response.text)} bytes")
        print(f"   Response Content: {response.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")
        return False

    # Test 2: Extract session ID and use it immediately
    print("\n2. Getting session ID...")
    try:
        response = requests.get(
            f"{BASE_URL}/sse",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=5
        )

        # Parse SSE response
        content = response.text
        print(f"   SSE Response: {content}")

        # Look for session ID in various formats
        import re
        session_match = re.search(r'sessionId=([a-f0-9\-]+)', content)
        if session_match:
            session_id = session_match.group(1)
            print(f"   Found Session ID: {session_id}")
        else:
            print("   No session ID found in response")
            return False

    except Exception as e:
        print(f"   Error getting session: {e}")
        return False

    # Test 3: Try to list tools
    print(f"\n3. Testing tools/list with session: {session_id}")
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }

        response = requests.post(
            f"{BASE_URL}/message?sessionId={session_id}",
            json=payload,
            headers={
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=10
        )

        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")

    except Exception as e:
        print(f"   Error: {e}")

    # Test 4: Try to search for the directory
    print(f"\n4. Searching for '260715' directory...")
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "pan_searchFileByParentId",
                "arguments": {
                    "parentId": "/",
                    "keyword": "260715",
                    "page": 1,
                    "pageSize": 20
                }
            }
        }

        response = requests.post(
            f"{BASE_URL}/message?sessionId={session_id}",
            json=payload,
            headers={
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=10
        )

        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")

        # Parse response
        try:
            result = response.json()
            print(f"\n   Parsed JSON result:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            # Check if we found the directory
            if "result" in result and "content" in result["result"]:
                print(f"\n   SUCCESS! Search completed. Checking for '260715' directory...")
                # Check the content for our target directory
                for item in result["result"].get("content", []):
                    if "text" in item:
                        print(f"   Result text: {item['text']}")
        except:
            print(f"   Could not parse JSON response")

    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_baidu_mcp()