"""
wxchat-article功能配置验证脚本

验证所有必需的配置项是否正确设置：
1. 核心wxchat配置
2. SFTP上传路径配置
3. 钉钉通知配置
4. 数据库配置
5. PDF生成相关配置

Author: Task 8 Configuration Verification
Date: 2026-08-21
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings


class ConfigVerification:
    """配置验证类"""

    def __init__(self):
        """初始化验证器"""
        self.settings = Settings()
        self.missing_configs = []
        self.invalid_configs = []
        self.optional_configs = []
        self.verification_results = {}

    def verify_required_config(self, config_name: str, config_value, description: str = "") -> bool:
        """
        验证必需配置项

        Args:
            config_name: 配置名称
            config_value: 配置值
            description: 配置描述

        Returns:
            是否验证通过
        """
        is_valid = config_value is not None and config_value != ''
        result = {
            'name': config_name,
            'value': str(config_value) if config_value else 'None',
            'description': description,
            'valid': is_valid,
            'required': True
        }

        self.verification_results[config_name] = result

        if not is_valid:
            self.missing_configs.append(config_name)
            return False

        return True

    def verify_optional_config(self, config_name: str, config_value, default_value, description: str = "") -> bool:
        """
        验证可选配置项

        Args:
            config_name: 配置名称
            config_value: 配置值
            default_value: 默认值
            description: 配置描述

        Returns:
            是否验证通过
        """
        is_valid = config_value is not None
        has_default = config_value == default_value
        result = {
            'name': config_name,
            'value': str(config_value) if config_value else 'None',
            'description': description,
            'valid': is_valid,
            'required': False,
            'is_default': has_default
        }

        self.verification_results[config_name] = result

        if not is_valid:
            self.optional_configs.append(config_name)
            return False

        return True

    def verify_numeric_config(self, config_name: str, config_value, min_value: int = None, max_value: int = None, description: str = "") -> bool:
        """
        验证数值型配置

        Args:
            config_name: 配置名称
            config_value: 配置值
            min_value: 最小值
            max_value: 最大值
            description: 配置描述

        Returns:
            是否验证通过
        """
        is_valid = config_value is not None

        if is_valid and min_value is not None:
            is_valid = config_value >= min_value

        if is_valid and max_value is not None:
            is_valid = config_value <= max_value

        result = {
            'name': config_name,
            'value': str(config_value) if config_value is not None else 'None',
            'description': description,
            'valid': is_valid,
            'required': True
        }

        self.verification_results[config_name] = result

        if not is_valid:
            self.invalid_configs.append(config_name)
            return False

        return True

    def run_verification(self):
        """运行完整配置验证"""
        print("🔍 开始wxchat-article功能配置验证")
        print("=" * 80)

        # 1. 核心wxchat配置
        print("\n📱 核心wxchat配置:")
        print("-" * 40)

        self.verify_required_config(
            'wxchat_enabled',
            self.settings.wxchat_enabled,
            '是否启用wxchat功能'
        )

        self.verify_required_config(
            'wxchat_sftp_remote_path',
            self.settings.wxchat_sftp_remote_path,
            'SFTP远程基础路径（如：/wxchat）'
        )

        self.verify_required_config(
            'wxchat_base_url',
            self.settings.wxchat_base_url,
            '微信文章基础URL'
        )

        # 2. PDF生成相关配置
        print("\n📄 PDF生成配置:")
        print("-" * 40)

        self.verify_numeric_config(
            'wxchat_pdf_timeout',
            self.settings.wxchat_pdf_timeout,
            min_value=10,
            max_value=600,
            description='PDF生成超时时间（秒）'
        )

        self.verify_numeric_config(
            'wxchat_image_wait_time',
            self.settings.wxchat_image_wait_time,
            min_value=5,
            max_value=60,
            description='图片加载等待时间（秒）'
        )

        self.verify_numeric_config(
            'wxchat_download_delay',
            self.settings.wxchat_download_delay,
            min_value=1,
            max_value=30,
            description='下载延迟时间（秒）'
        )

        self.verify_numeric_config(
            'max_pdf_size_mb',
            self.settings.max_pdf_size_mb,
            min_value=10,
            max_value=500,
            description='PDF文件最大大小（MB）'
        )

        # 3. SFTP配置
        print("\n📤 SFTP上传配置:")
        print("-" * 40)

        self.verify_required_config(
            'sftp_host',
            self.settings.sftp_host,
            'SFTP服务器地址'
        )

        self.verify_numeric_config(
            'sftp_port',
            self.settings.sftp_port,
            min_value=1,
            max_value=65535,
            description='SFTP端口'
        )

        self.verify_required_config(
            'sftp_username',
            self.settings.sftp_username,
            'SFTP用户名'
        )

        self.verify_required_config(
            'sftp_password',
            self.settings.sftp_password,
            'SFTP密码（显示为****）'
        )

        self.verify_required_config(
            'sftp_remote_path',
            self.settings.sftp_remote_path,
            'SFTP远程基础路径'
        )

        # 4. 钉钉通知配置
        print("\n📱 钉钉通知配置:")
        print("-" * 40)

        has_dingtalk_config = False
        if self.settings.dingtalk_webhook:
            has_dingtalk_config = True
            self.verify_required_config(
                'dingtalk_webhook',
                self.settings.dingtalk_webhook,
                '钉钉Webhook地址'
            )

        if self.settings.dingtalk_app_key:
            has_dingtalk_config = True
            self.verify_required_config(
                'dingtalk_app_key',
                self.settings.dingtalk_app_key,
                '钉钉AppKey'
            )

        if self.settings.dingtalk_app_secret:
            self.verify_required_config(
                'dingtalk_app_secret',
                self.settings.dingtalk_app_secret,
                '钉钉AppSecret'
            )

        self.verify_optional_config(
            'dingtalk_chat_id',
            self.settings.dingtalk_chat_id,
            '',
            '钉钉群聊ID（可选）'
        )

        if not has_dingtalk_config:
            print("⚠️  警告: 未配置钉钉通知，将无法发送反馈通知")

        # 5. 数据库配置
        print("\n💾 数据库配置:")
        print("-" * 40)

        self.verify_required_config(
            'db_host',
            self.settings.db_host,
            '数据库服务器地址'
        )

        self.verify_numeric_config(
            'db_port',
            self.settings.db_port,
            min_value=1,
            max_value=65535,
            description='数据库端口'
        )

        self.verify_required_config(
            'db_user',
            self.settings.db_user,
            '数据库用户名'
        )

        self.verify_required_config(
            'db_password',
            self.settings.db_password,
            '数据库密码（显示为****）'
        )

        self.verify_required_config(
            'db_name',
            self.settings.db_name,
            '数据库名称'
        )

        # 6. 消息重试配置
        print("\n🔄 消息重试配置:")
        print("-" * 40)

        self.verify_numeric_config(
            'max_message_retries',
            self.settings.max_message_retries,
            min_value=1,
            max_value=100,
            description='消息最大重试次数'
        )

        self.verify_numeric_config(
            'retry_max_attempts',
            self.settings.retry_max_attempts,
            min_value=1,
            max_value=10,
            description='操作最大重试次数'
        )

        # 7. 检查wxchat相关表配置
        print("\n📊 数据库表配置检查:")
        print("-" * 40)

        try:
            from src.database.models import DatabaseManager
            db_manager = DatabaseManager(self.settings)
            tables = db_manager.get_all_tables()

            has_messages = 'messages' in tables
            has_transfers = 'transfers' in tables

            print(f"✅ messages表存在: {has_messages}")
            print(f"✅ transfers表存在: {has_transfers}")

            if not has_messages or not has_transfers:
                print("⚠️  警告: 缺少必需的数据库表")

        except Exception as e:
            print(f"❌ 数据库表检查失败: {e}")

        # 打印验证结果摘要
        self.print_verification_summary()

    def print_verification_summary(self):
        """打印验证结果摘要"""
        print("\n" + "=" * 80)
        print("📊 配置验证结果摘要")
        print("=" * 80)

        total_configs = len(self.verification_results)
        required_valid = sum(1 for result in self.verification_results.values()
                            if result['required'] and result['valid'])
        total_required = sum(1 for result in self.verification_results.values()
                           if result['required'])

        print(f"\n总配置项: {total_configs}")
        print(f"必需配置: {total_required}")
        print(f"必需配置有效: {required_valid}")
        print(f"缺失配置: {len(self.missing_configs)}")
        print(f"无效配置: {len(self.invalid_configs)}")

        # 详细问题列表
        if self.missing_configs:
            print(f"\n❌ 缺失的必需配置:")
            for config_name in self.missing_configs:
                result = self.verification_results[config_name]
                print(f"   - {config_name}: {result['description']}")

        if self.invalid_configs:
            print(f"\n⚠️  无效的配置:")
            for config_name in self.invalid_configs:
                result = self.verification_results[config_name]
                print(f"   - {config_name}: {result['description']} (值: {result['value']})")

        if self.optional_configs:
            print(f"\nℹ️  缺失的可选配置:")
            for config_name in self.optional_configs:
                result = self.verification_results[config_name]
                print(f"   - {config_name}: {result['description']}")

        # 部署就绪判断
        print(f"\n🎯 配置验证结果:")
        if len(self.missing_configs) == 0 and len(self.invalid_configs) == 0:
            print("✅ 配置完整且有效，可以进行部署")
            return True
        elif len(self.missing_configs) > 0:
            print("❌ 存在缺失的必需配置，请补充后部署")
            return False
        else:
            print("⚠️  存在无效配置，请修正后部署")
            return False

    def print_config_table(self):
        """打印配置表格"""
        print("\n📋 详细配置信息表:")
        print("-" * 80)

        # 表头
        print(f"{'配置名称':<25} {'值':<30} {'状态':<8} {'描述'}")
        print("-" * 80)

        # 配置行
        for result in self.verification_results.values():
            status = "✅" if result['valid'] else "❌"
            if not result['required']:
                status += "(可选)"

            value = result['value']
            if 'password' in result['name'].lower() or 'secret' in result['name'].lower():
                if value and value != 'None':
                    value = '****'

            print(f"{result['name']:<25} {value:<30} {status:<8} {result['description']}")

        print("-" * 80)


def main():
    """主函数"""
    try:
        verifier = ConfigVerification()
        verifier.run_verification()
        verifier.print_config_table()
        return 0
    except Exception as e:
        print(f"❌ 配置验证异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())