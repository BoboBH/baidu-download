#!/usr/bin/env python3
"""
Hybrid test using curl for SSE and Python for search
"""

import subprocess
import requests
import json
import time

def get_session_id_curl():
    """Get session ID using curl"""
    print("Getting session ID via curl...")
    try:
        cmd = [
            'curl', '-s',
            '-H', 'Authorization: Bearer 123.e4ecb1648bd7452260db272f4465448b.Y7DN7-4DoSGomdNHW_qvUfnKPqnZJBkrU2F8ZLw.ihRBUQ',
            '--max-time', '5',
            'https://mcp-pan.baidu.com/sse'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = result.stdout

        print(f"Curl output: {output}")

        # Extract session ID
        import re
        session_match = re.search(r'sessionId=([a-f0-9\-]+)', output)
        if session_match:
            session_id = session_match.group(1)
            print(f"Session ID extracted: {session_id}")
            return session_id
        else:
            print("No session ID found")
            return None

    except Exception as e:
        print(f"Error getting session: {e}")
        return None

def search_directory(session_id):
    """Search for 260715 directory"""
    print(f"Searching for '260715' directory...")
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
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
            f"https://mcp-pan.baidu.com/message?sessionId={session_id}",
            json=payload,
            headers={
                "Authorization": "Bearer 123.e4ecb1648bd7452260db272f4465448b.Y7DN7-4DoSGomdNHW_qvUfnKPqnZJBkrU2F8ZLw.ihRBUQ",
                "Content-Type": "application/json"
            },
            timeout=10
        )

        print(f"Search response status: {response.status_code}")
        print(f"Response: {response.text}")

        result = response.json()
        print(f"\nParsed result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if "result" in result:
            print("\n[SUCCESS] Search request completed successfully!")
            print("Looking for '260715' directory in results...")

            if "content" in result["result"]:
                for item in result["result"]["content"]:
                    if "text" in item:
                        print(f"Found: {item['text']}")
                        if "260715" in item['text']:
                            print("[MATCH] '260715' directory found!")
                            return True
                print("[INFO] '260715' not explicitly mentioned in results")
                return False
        elif "error" in result:
            print(f"[ERROR] Search failed: {result['error']}")
            return False

    except Exception as e:
        print(f"Error during search: {e}")
        return False

def main():
    print("=" * 50)
    print("Hybrid Baidu Pan MCP Test")
    print("Searching for '260715' directory")
    print("=" * 50)

    # Get session ID via curl
    session_id = get_session_id_curl()

    if not session_id:
        print("\n[FAIL] Could not obtain session ID")
        return

    # Search immediately
    success = search_directory(session_id)

    print("\n" + "=" * 50)
    if success:
        print("[FINAL RESULT] Test PASSED - '260715' directory found")
    else:
        print("[FINAL RESULT] Test INCOMPLETE - Could not confirm '260715' directory")
    print("=" * 50)

if __name__ == "__main__":
    main()