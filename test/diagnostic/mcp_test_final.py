#!/usr/bin/env python3
"""
Baidu Pan MCP Server Test - Final Diagnostic Summary
Tests searching for '260715' directory in root
"""

import requests
import json
import sys

def test_baidu_mcp_final():
    """Final comprehensive test of Baidu Pan MCP Server"""
    print("=" * 60)
    print("Baidu Pan MCP Server - Final Diagnostic Test")
    print("Testing: Search for '260715' directory in root")
    print("=" * 60)

    AUTH_TOKEN = "123.e4ecb1648bd7452260db272f4465448b.Y7DN7-4DoSGomdNHW_qvUfnKPqnZJBkrU2F8ZLw.ihRBUQ"
    BASE_URL = "https://mcp-pan.baidu.com"

    # Test Results Summary
    results = []

    # Test 1: Basic Connectivity
    print("\n[1] Testing basic connectivity...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"    Root endpoint status: {response.status_code}")
        results.append(("Basic connectivity", "PASS" if response.status_code in [200, 403] else "FAIL"))
    except Exception as e:
        print(f"    Error: {e}")
        results.append(("Basic connectivity", "FAIL"))

    # Test 2: SSE Endpoint Accessibility
    print("\n[2] Testing SSE endpoint with authorization...")
    try:
        response = requests.get(
            f"{BASE_URL}/sse",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=8
        )
        print(f"    SSE endpoint status: {response.status_code}")
        print(f"    Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"    Response: {response.text[:100]}")
        results.append(("SSE endpoint access", "PASS" if response.status_code == 200 else "FAIL"))

        # Extract session ID
        import re
        session_match = re.search(r'sessionId=([a-f0-9\-]+)', response.text)
        session_id = session_match.group(1) if session_match else None
        print(f"    Session ID found: {session_id}")

    except Exception as e:
        print(f"    Error: {e}")
        results.append(("SSE endpoint access", "FAIL"))
        session_id = None

    # Test 3: Session Validation
    if session_id:
        print(f"\n[3] Testing session ID validation: {session_id}")
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
                timeout=10
            )

            print(f"    Search request status: {response.status_code}")
            print(f"    Response: {response.text}")

            result = response.json()
            print(f"    Parsed result:")
            print(json.dumps(result, indent=4, ensure_ascii=False))

            if "result" in result:
                results.append(("Search functionality", "PASS"))
                print("\n[SUCCESS] Search request completed successfully!")
                print("Checking for '260715' directory...")

                # Look for directory in results
                if "content" in result["result"]:
                    for item in result["result"]["content"]:
                        if "text" in item:
                            print(f"Result: {item['text']}")
            elif "error" in result:
                results.append(("Search functionality", "FAIL"))
                print(f"[ERROR] Search failed: {result['error']}")

        except Exception as e:
            print(f"    Error: {e}")
            results.append(("Search functionality", "ERROR"))

    else:
        print("\n[3] Skipping session validation - no session ID obtained")
        results.append(("Search functionality", "SKIPPED"))

    # Final Summary
    print("\n" + "=" * 60)
    print("FINAL TEST RESULTS:")
    print("=" * 60)
    for test_name, result in results:
        status_symbol = "[OK]" if result == "PASS" else "[FAIL]" if result == "FAIL" else f"[{result}]"
        print(f"{status_symbol} {test_name}: {result}")

    print("\nCONCLUSION:")
    if any(r[1] == "PASS" for r in results):
        print("Partially working - Some components are functional")
    else:
        print("Not working - Major connectivity or authentication issues detected")
    print("=" * 60)

if __name__ == "__main__":
    test_baidu_mcp_final()