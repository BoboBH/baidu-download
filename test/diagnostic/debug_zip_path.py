"""
Debug ZIP file path creation
"""
import os
import zipfile
from pathlib import Path

# Test the specific path that's failing
test_extract_dir = r"C:\Users\bobo\AppData\Local\Temp\dingtalk_download_test\2-reports"
test_decoded_name = "Goldman Sachs-Taiwan Weekly Kickstart滑TAIEX slumped 6_ amid continued tech~sector risk~off sentiment despite stronger TSMC guidance糯with foreign outflows from Taiwan remaining significant 膳US$8bn.pdf"

final_path = os.path.join(test_extract_dir, test_decoded_name)
print(f"Final path length: {len(final_path)}")
print(f"Final path: {final_path}")

# Check Windows path length limit (260 chars normally, 32767 with extended-length syntax)
if len(final_path) > 260:
    print(f"WARNING: Path exceeds Windows 260 character limit!")

# Try to create the file
try:
    # Create parent dir
    os.makedirs(test_extract_dir, exist_ok=True)
    print(f"Created extract dir: {test_extract_dir}")

    # Try to create the file
    with open(final_path, 'w') as f:
        f.write("test content")
    print(f"SUCCESS: Created file at {final_path}")

    # Clean up
    if os.path.exists(final_path):
        os.remove(final_path)
    if os.path.exists(test_extract_dir):
        os.rmdir(test_extract_dir)

except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
    print(f"Error path: {final_path}")
