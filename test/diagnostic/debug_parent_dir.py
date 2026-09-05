"""
Debug parent directory creation
"""
import os
import sys
from pathlib import Path

# Setup project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test the parent directory logic
test_extract_dir = r"C:\Users\bobo\AppData\Local\Temp\dingtalk_download_test\2-reports"
test_decoded_name = "Goldman Sachs-Taiwan Weekly Kickstart滑TAIEX slumped 6_ amid continued tech~sector risk~off sentiment despite stronger TSMC guidance糯with foreign outflows from Taiwan remaining significant 膳US$8bn.pdf"

final_path = os.path.join(test_extract_dir, test_decoded_name)
print(f"Final path: {final_path}")

final_parent_dir = os.path.dirname(final_path)
print(f"Parent dir: {final_parent_dir}")
print(f"Parent dir exists: {os.path.exists(final_parent_dir)}")

# Test creation
if final_parent_dir and not os.path.exists(final_parent_dir):
    print(f"Creating parent directory: {final_parent_dir}")
    os.makedirs(final_parent_dir, exist_ok=True)
    print(f"Created successfully: {os.path.exists(final_parent_dir)}")
