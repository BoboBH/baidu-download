#!/usr/bin/env python3
"""
测试PDF文件检测问题
"""
import subprocess
import re

def run_baidu_command(command_parts):
    """运行BaiduPCS-Go命令"""
    full_command = ['BaiduPCS-Go.exe'] + command_parts
    print(f"\n运行命令: {' '.join(full_command)}")

    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=60
        )

        print(f"返回码: {result.returncode}")
        if result.stdout:
            print(f"标准输出:\n{result.stdout}")
        if result.stderr:
            print(f"标准错误:\n{result.stderr}")

        return result
    except Exception as e:
        print(f"命令执行异常: {e}")
        return None

def test_ls_format(folder_name):
    """测试ls命令输出格式"""
    print(f"\n{'='*60}")
    print(f"测试目录: {folder_name}")
    print(f"{'='*60}")

    result = run_baidu_command(['ls', f'//{folder_name}'])

    if result and result.returncode == 0:
        print(f"\n{'='*60}")
        print("解析PDF文件:")
        print(f"{'='*60}")

        pdf_files = []
        for line in result.stdout.split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or '----' in line or '当前目录' in line:
                continue

            print(f"\n处理行: {line}")

            # 使用正则表达式匹配
            match = re.match(r'^(\d+)\s+([\d.]+\s*[KBMG]+)\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(.+)$', line)
            if match:
                parts = list(match.groups())
                file_name = parts[4]
                file_size_str = parts[1]

                print(f"  匹配成功!")
                print(f"  序号: {parts[0]}")
                print(f"  大小: {file_size_str}")
                print(f"  日期: {parts[2]}")
                print(f"  时间: {parts[3]}")
                print(f"  文件名: {file_name}")

                # 检查是否为PDF文件
                if file_name.lower().endswith('.pdf') and not file_name.endswith('/'):
                    print(f"  ✅ 这是PDF文件!")
                    pdf_files.append({
                        'name': file_name,
                        'size': file_size_str
                    })
                else:
                    print(f"  ❌ 不是PDF文件")
            else:
                print(f"  ❌ 正则匹配失败")

        print(f"\n{'='*60}")
        print(f"找到 {len(pdf_files)} 个PDF文件")
        print(f"{'='*60}")
        for i, pdf in enumerate(pdf_files, 1):
            print(f"{i}. {pdf['name']} ({pdf['size']})")
    else:
        print("❌ ls命令执行失败")

if __name__ == '__main__':
    # 测试你的目录
    test_ls_format("260713")

    print("\n" + "="*60)
    print("建议检查:")
    print("="*60)
    print("1. 分享链接是否真的包含PDF文件")
    print("2. 目录是否转存成功")
    print("3. 运行程序时查看详细日志")
    print("4. 检查BaiduPCS-Go的ls输出格式是否符合预期")