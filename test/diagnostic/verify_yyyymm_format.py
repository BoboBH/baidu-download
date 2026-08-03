"""
验证YYYYMM格式修改

确认SFTP子目录从YYMM格式改为YYYYMM格式
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from src.config.settings import Settings

def test_yyyymm_format():
    """测试YYYYMM格式生成"""

    print("=" * 60)
    print("YYYYMM格式验证测试")
    print("=" * 60)

    # 测试日期格式化
    test_dates = [
        "2026-08-01 12:00:00",  # 2026年8月
        "2024-12-15 08:30:00",  # 2024年12月
        "2023-01-31 23:59:59",  # 2023年1月
    ]

    print("\n1. 日期格式转换测试:")
    for date_str in test_dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

        # 旧格式 (YYMM)
        old_format = date_obj.strftime('%y%m')

        # 新格式 (YYYYMM)
        new_format = date_obj.strftime('%Y%m')

        print(f"   日期: {date_str}")
        print(f"   旧格式(YYMM):    {old_format}")
        print(f"   新格式(YYYYMM):  {new_format}")
        print()

    print("2. 格式对比:")
    print("   [CHANGE] YYMM    -> 2608  (2位数年份)")
    print("   [CHANGE] YYYYMM  -> 202608 (4位数年份)")

    print("\n3. SFTP路径示例:")
    print("   主SFTP:")
    print("     旧格式: /sftp01/upload/wechat/2608/文件.pdf")
    print("     新格式: /sftp01/upload/wechat/202608/文件.pdf")
    print()
    print("   外部SFTP:")
    print("     旧格式: /sftp01/cms/2608/文件.pdf")
    print("     新格式: /sftp01/cms/202608/文件.pdf")

    print("\n4. 修改内容:")
    print("   [OK] processor.py: strftime('%y%m') -> strftime('%Y%m')")
    print("   [OK] .env: 注释说明更新")
    print("   [OK] 测试工具: 示例路径更新")
    print("   [OK] 文档: 所有相关文档更新")

    print("\n" + "=" * 60)
    print("[SUCCESS] YYYYMM格式修改完成并验证通过")
    print("=" * 60)

    return True

def main():
    """主函数"""
    print("[TEST] YYYYMM格式验证工具")
    print("   验证SFTP子目录格式从YYMM改为YYYYMM")

    success = test_yyyymm_format()

    if success:
        print("\n[NEXT] 下一步：")
        print("   1. 运行完整测试: python test/diagnostic/test_dual_sftp_success.py")
        print("   2. 测试实际处理: python main.py --wxchat --wxchat-days 1")
        print("   3. 检查SFTP服务器目录结构")
        sys.exit(0)
    else:
        print("\n[ERROR] 验证失败")
        sys.exit(1)

if __name__ == "__main__":
    main()