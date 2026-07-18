#!/usr/bin/env python3
"""
测试设置文件修复
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.config.settings import Settings
    print("✅ Settings 类导入成功")

    # 测试设置加载
    settings = Settings()
    print("✅ Settings 实例创建成功")

    # 检查路径
    print(f"📁 BaiduPCS-Go 路径: {settings.baidupcs_go_path}")
    print(f"📁 Cookies 路径: {settings.baidu_cookies_path}")
    print(f"📁 临时目录: {settings.temp_dir}")

    # 验证文件是否存在
    if Path(settings.baidupcs_go_path).exists():
        print(f"✅ BaiduPCS-Go 文件存在")
    else:
        print(f"❌ BaiduPCS-Go 文件不存在: {settings.baidupcs_go_path}")

    if Path(settings.baidu_cookies_path).exists():
        print(f"✅ Cookies 文件存在")
    else:
        print(f"❌ Cookies 文件不存在: {settings.baidu_cookies_path}")

    print("\n🎉 设置修复测试完成！")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
