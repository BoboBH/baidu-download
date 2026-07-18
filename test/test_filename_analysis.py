# 分析文件名结构
import re

# 完整路径
full_path = "d:/f/901741041_Bobo_Huang123/Goldman Sachs-EM Weekly Fund Flows Monitor：Foreign selling continues driven by North Asia， while Southbound flows stay strong； HF de~grossing continues in July， while MFs rotate exposure to India in June； Korea Leveraged Flows Update-260717.pdf"

# 分解路径结构
parts = full_path.split('/')
print("路径结构分析：")
for i, part in enumerate(parts):
    print(f"  [{i}] '{part}' (长度: {len(part)})")

# 用户ID部分
user_id_part = parts[1]  # "901741041_Bobo_Huang123"
print(f"\n用户ID部分: '{user_id_part}'")

# 提取用户ID数字
user_number = re.search(r'(\d+)', user_id_part)
if user_number:
    user_id = user_number.group(1)
    print(f"   用户数字: {user_id}")

# 文件名部分
filename = parts[-1]
print(f"\n原始文件名:")
print(f"   长度: {len(filename)} 字符")
print(f"   内容: {filename[:80]}...")

# 提取关键信息
file_date = re.search(r'(\d{6})\.pdf$', filename)  # 匹配末尾日期
if file_date:
    date_str = file_date.group(1)
    print(f"   日期: {date_str}")

# 机构信息
institution = "Goldman_Sachs" if "Goldman" in filename else ""
print(f"   机构: {institution}")

# 文档类型
doc_type = ""
if "Weekly" in filename:
    doc_type = "Weekly"
elif "Monthly" in filename:
    doc_type = "Monthly"
elif "Daily" in filename:
    doc_type = "Daily"
print(f"   类型: {doc_type}")

# 主题
subject = "Fund_Flows" if "Fund Flows" in filename else "Report"
print(f"   主题: {subject}")

print(f"\n建议的简化文件名:")

# 方案1: 使用完整用户ID
suggested1 = f"{user_id_part}_{institution}_{subject}_{date_str}.pdf"
print(f"   1. {suggested1}")
print(f"      长度: {len(suggested1)} 字符")

# 方案2: 仅用户数字
suggested2 = f"{user_id}_{institution}_{subject}_{date_str}.pdf"
print(f"   2. {suggested2}")
print(f"      长度: {len(suggested2)} 字符")

# 方案3: 最简版本
suggested3 = f"{user_id}_{doc_type[0]}{subject[0]}_{date_str}.pdf"
print(f"   3. {suggested3}")
print(f"      长度: {len(suggested3)} 字符")

# 方案4: 哈希版本
import hashlib
hash_input = f"{user_id}_{filename}".encode('utf-8')
file_hash = hashlib.md5(hash_input).hexdigest()[:6]
suggested4 = f"{user_id}_{file_hash}_{date_str}.pdf"
print(f"   4. {suggested4}")
print(f"      长度: {len(suggested4)} 字符")

print(f"\n推荐: 方案2 (简化用户ID)")
print(f"   原因: 保持唯一性，大幅缩短，便于识别")
