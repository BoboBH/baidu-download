#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试：_download_with_normal_flow 方法
允许用户自定义 remote_path 和 local_path 来调试超长文件名下载问题
"""

import os
import sys
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config.settings import Settings
from src.downloader.baidu_client import BaiduClient

def setup_logging():
    """设置详细日志"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('test_download_normal_flow.log', encoding='utf-8')
        ]
    )

def test_download_normal_flow(remote_path, local_path):
    """
    测试 _download_with_normal_flow 方法

    Args:
        remote_path: 百度网盘中的文件路径
        local_path: 本地保存路径
    """
    logger = logging.getLogger(__name__)

    try:
        logger.info("=" * 60)
        logger.info("🧪 测试 _download_with_normal_flow 方法")
        logger.info("=" * 60)

        logger.info(f"📝 参数配置:")
        logger.info(f"  remote_path: {remote_path}")
        logger.info(f"  local_path: {local_path}")

        # 初始化配置（用于显示信息）
        settings = Settings()
        logger.info(f"📋 配置信息:")
        logger.info(f"  TEMP_DIR: {settings.temp_dir}")
        logger.info(f"  BaiduPCS-Go: {settings.baidupcs_go_path}")
        logger.info(f"📋 配置信息:")
        logger.info(f"  TEMP_DIR: {settings.temp_dir}")
        logger.info(f"  BaiduPCS-Go: {settings.baidupcs_go_path}")

        # 初始化 BaiduClient (不需要传入settings，它会自己创建Settings实例)
        baidu_client = BaiduClient()

        # 登录百度账号
        logger.info(f"🔐 正在登录百度账号...")
        if baidu_client.login():
            logger.info(f"✅ 登录成功")
        else:
            logger.error(f"❌ 登录失败")
            return False

        # 执行测试方法
        logger.info(f"🚀 开始测试 _download_with_normal_flow...")
        result = baidu_client._download_with_normal_flow(remote_path, local_path)

        # 验证结果
        logger.info(f"📊 测试结果:")
        logger.info(f"  返回值: {result}")

        if os.path.exists(local_path):
            file_size = os.path.getsize(local_path)
            logger.info(f"  ✅ 文件存在: {local_path}")
            logger.info(f"  📁 文件大小: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
        else:
            logger.warning(f"  ❌ 文件不存在: {local_path}")

        return result

    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_print_variables(**kwargs):
    """调试打印变量的辅助函数"""
    print("\n" + "=" * 60)
    print("🔍 调试变量信息:")
    for key, value in kwargs.items():
        print(f"  🔍 {key} = {value}")
        if isinstance(value, str):
            print(f"     类型: str, 长度: {len(value)}")
        elif isinstance(value, (int, float, bool)):
            print(f"     类型: {type(value).__name__}")
        elif value is None:
            print(f"     类型: None")
        else:
            print(f"     类型: {type(value).__name__}")
    print("=" * 60 + "\n")

def main():
    """主函数：用户可配置参数"""
    setup_logging()
    logger = logging.getLogger(__name__)

    # ========================================
    # 🔧 用户配置区域 - 请修改以下参数
    # ========================================
    #
    # ⚠️ 重要说明：
    # 1. _download_with_normal_flow() 方法用于下载重命名后的短文件名
    # 2. 测试前，您需要先在百度网盘中手动重命名文件为短文件名
    # 3. 或者先使用 _download_long_filename() 方法进行完整测试
    #
    # 🔧 手动重命名步骤（可选）：
    #    在百度网盘中将超长文件重命名为：temp_download_abc123.pdf
    #
    # ========================================

    # 测试用例1：超长文件名（重命名后的短文件名）
    test_cases = [
        {
            "name": "测试1：重命名后的短文件名",
            "remote_path": "//260807/Goldman Sachs-Nintendo （7974.T） 1Q results： Modestly above expectations even excluding tariff refunds； Switch software strong and annual playing users remain at high levels； raise earnings estimates， Buy-260807.pdf",  # 你在百度网盘中重命名后的短文件名
            "local_path": "d:/f/Goldman Sachs-Nintendo （7974.T） 1Q results： Modestly above expectations even excluding tariff refunds； Switch software strong and annual playing users remain at high levels； raise earnings estimates， Buy-260807.pdf"  # 本地保存路径
        }
    ]

    # 或者你可以直接指定单个测试：
    # remote_path = "//260807/temp_download_60497207.pdf"  # 修改为你的实际路径
    # local_path = "d:/f/test_normal_flow.pdf"  # 修改为你的实际路径
    # ========================================

    logger.info("🎯 开始执行测试用例...")

    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"执行测试用例 {i}: {test_case['name']}")
        logger.info(f"{'='*60}")

        success = test_download_normal_flow(
            test_case['remote_path'],
            test_case['local_path']
        )

        if success:
            logger.info(f"✅ 测试用例 {i} 成功")
        else:
            logger.error(f"❌ 测试用例 {i} 失败")

    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 所有测试完成")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    main()