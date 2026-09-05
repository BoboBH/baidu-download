#!/usr/bin/env python3
import requests
import json
import re
import time

# Configuration
AUTH_TOKEN = "123.e4ecb1648bd7452260db272f4465448b.Y7DN7-4DoSGomdNHW_qvUfnKPqnZJBkrU2F8ZLw.ihRBUQ"
BASE_URL = "https://mcp-pan.baidu.com"
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def get_session_id():
    """Get a fresh session ID from the SSE endpoint"""
    try:
        response = requests.get(
            f"{BASE_URL}/sse",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=5
        )

        # Parse SSE response to extract session ID
        content = response.text
        match = re.search(r'sessionId=([a-f0-9\-]+)', content)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        print(f"Error getting session ID: {e}")
        return None

def search_directory(session_id, keyword="260715"):
    """Search for directory in root"""
    try:
        url = f"{BASE_URL}/message?sessionId={session_id}"
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "pan_searchFileByParentId",
                "arguments": {
                    "parentId": "/",
                    "keyword": keyword,
                    "page": 1,
                    "pageSize": 20
                }
            }
        }

        response = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error searching directory: {e}")
        return None

def main():
    print("Testing Baidu Pan MCP Server - Search for '260715' directory")
    print("=" * 60)

    # Get fresh session
    print("1. Getting session ID...")
    session_id = get_session_id()
    if not session_id:
        print("Failed to get session ID")
        return

    print(f"Session ID obtained: {session_id}")

    # Search for directory
    print(f"2. Searching for '260715' directory in root...")
    result = search_directory(session_id, "260715")

    if result:
        print("3. Search Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Check if search was successful
        if "result" in result:
            print("\nSearch successful!")
            if "content" in result["result"]:
                print(f"Found content in search result")
        elif "error" in result:
            print(f"\nSearch failed with error: {result['error']}")
    else:
        print("No response received")

if __name__ == "__main__":
    main()