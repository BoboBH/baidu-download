#!/usr/bin/env python3
import requests
import json
import time
import re

# Configuration
AUTH_TOKEN = "123.e4ecb1648bd7452260db272f4465448b.Y7DN7-4DoSGomdNHW_qvUfnKPqnZJBkrU2F8ZLw.ihRBUQ"
BASE_URL = "https://mcp-pan.baidu.com"

def diagnose_mcp_connection():
    """Diagnose Baidu Pan MCP connection issues"""
    print("Baidu Pan MCP Diagnostic Tool")
    print("=" * 50)

    # Test 1: Basic connectivity
    print("\n[Test 1] Basic connectivity to mcp-pan.baidu.com")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        print(f"[OK] Server reachable - Status: {response.status_code}")
    except requests.exceptions.Timeout:
        print("[FAIL] Connection timed out")
        return
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return

    # Test 2: SSE endpoint with different timeouts
    print("\n[Test 2] SSE endpoint with extended timeout")
    for timeout_val in [10, 20, 30]:
        try:
            print(f"  Trying with {timeout_val}s timeout...")
            response = requests.get(
                f"{BASE_URL}/sse",
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                timeout=timeout_val
            )
            print(f"  [OK] Success with {timeout_val}s - Got {len(response.text)} bytes")
            print(f"  Content: {response.text[:200]}")

            # If we got here, try to use this session
            if response.text:
                test_search_with_session(response.text)
                return

        except requests.exceptions.Timeout:
            print(f"  [FAIL] Timed out with {timeout_val}s")
        except Exception as e:
            print(f"  [FAIL] Error with {timeout_val}s: {e}")

    # Test 3: Try different auth formats
    print("\n[Test 3] Trying different authorization formats")
    auth_formats = [
        f"Bearer {AUTH_TOKEN}",
        AUTH_TOKEN,
        f"Token {AUTH_TOKEN}"
    ]

    for auth_format in auth_formats:
        try:
            print(f"  Trying: {auth_format[:30]}...")
            response = requests.get(
                f"{BASE_URL}/sse",
                headers={"Authorization": auth_format},
                timeout=15
            )
            print(f"  [OK] Success with format - Got {len(response.text)} bytes")
            if response.text:
                test_search_with_session(response.text)
                return
        except Exception as e:
            print(f"  [FAIL] Failed: {str(e)[:50]}")

    print("\n[Conclusion] Could not establish connection to MCP server")

def test_search_with_session(sse_response):
    """Try to search for directory using session from SSE response"""
    print(f"\n[Search Test] Attempting to search for '260715' directory")

    session_match = re.search(r'sessionId=([a-f0-9\-]+)', sse_response)
    if not session_match:
        print("[FAIL] No session ID found in SSE response")
        return

    session_id = session_match.group(1)
    print(f"Session ID: {session_id}")

    # Try search immediately
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
            f"{BASE_URL}/message?sessionId={session_id}",
            json=payload,
            headers={
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=15
        )

        print(f"[OK] Search request completed - Status: {response.status_code}")
        print(f"Response: {response.text}")

        try:
            result = response.json()
            print(f"\nParsed JSON result:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            if "result" in result:
                print("\n[SUCCESS] SUCCESS! Search request processed successfully")
            elif "error" in result:
                print(f"\n[WARNING] Search returned error: {result['error']}")
        except:
            print(f"Could not parse JSON response")

    except Exception as e:
        print(f"[FAIL] Search failed: {e}")

if __name__ == "__main__":
    diagnose_mcp_connection()