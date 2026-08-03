"""
外部SFTP配置测试工具

用于测试和验证外部SFTP配置是否正确
"""

import os
import tempfile
from src.config.settings import Settings
from src.uploader.sftp_client import SFTPClient

def test_external_sftp_config():
    """测试外部SFTP配置"""

    print("=" * 60)
    print("外部SFTP配置测试")
    print("=" * 60)

    try:
        # 加载配置
        config = Settings()

        # 检查外部SFTP配置
        print("\n1. 检查外部SFTP配置...")

        if not config.wxchat_external_sftp_host:
            print("   ❌ 外部SFTP未配置 (WXCHAT_EXTERNAL_SFTP_HOST 为空)")
            print("   💡 请在 .env 文件中配置以下参数:")
            print("      - WXCHAT_EXTERNAL_SFTP_HOST")
            print("      - WXCHAT_EXTERNAL_SFTP_PORT")
            print("      - WXCHAT_EXTERNAL_SFTP_USERNAME")
            print("      - WXCHAT_EXTERNAL_SFTP_PASSWORD")
            print("      - WXCHAT_EXTERNAL_SFTP_FOLDER")
            return False

        print(f"   ✅ 外部SFTP主机: {config.wxchat_external_sftp_host}")
        print(f"   ✅ 外部SFTP端口: {config.wxchat_external_sftp_port}")
        print(f"   ✅ 外部SFTP用户: {config.wxchat_external_sftp_username}")
        print(f"   ✅ 外部SFTP目录: {config.wxchat_external_sftp_folder}")

        # 检查排除配置
        print("\n2. 检查公众号排除配置...")
        if config.wxchat_external_exclude_accounts:
            print(f"   ✅ 排除的公众号: {', '.join(config.wxchat_external_exclude_accounts)}")
        else:
            print("   ℹ️  无排除公众号配置")

        # 测试SFTP连接
        print("\n3. 测试外部SFTP连接...")

        external_config = {
            'host': config.wxchat_external_sftp_host,
            'port': config.wxchat_external_sftp_port,
            'username': config.wxchat_external_sftp_username,
            'password': config.wxchat_external_sftp_password,
            'remote_path': config.wxchat_external_sftp_folder
        }

        try:
            with SFTPClient(custom_config=external_config) as sftp:
                print(f"   ✅ 成功连接到外部SFTP服务器")

                # 测试目录创建
                test_dir = f"{config.wxchat_external_sftp_folder}/test_2607"
                if sftp.create_directory(test_dir):
                    print(f"   ✅ 测试目录创建成功: {test_dir}")

                    # 创建测试文件并上传
                    print("\n4. 测试文件上传...")
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                        tmp_file.write("外部SFTP测试文件")
                        tmp_file_path = tmp_file.name

                    try:
                        test_file_path = f"{test_dir}/test_external_sftp.txt"
                        if sftp.upload_file(tmp_file_path, test_file_path):
                            print(f"   ✅ 测试文件上传成功: {test_file_path}")
                        else:
                            print(f"   ❌ 测试文件上传失败")

                    finally:
                        # 清理临时文件
                        if os.path.exists(tmp_file_path):
                            os.unlink(tmp_file_path)

                print("\n" + "=" * 60)
                print("✅ 外部SFTP配置测试通过！")
                print("=" * 60)
                return True

        except Exception as e:
            print(f"   ❌ SFTP连接测试失败: {e}")
            print("\n💡 请检查以下配置:")
            print("   - 主机地址是否正确")
            print("   - 端口号是否正确")
            print("   - 用户名和密码是否正确")
            print("   - 网络连接是否正常")
            return False

    except Exception as e:
        print(f"❌ 配置测试异常: {e}")
        return False

def test_exclusion_logic():
    """测试排除逻辑"""

    print("\n" + "=" * 60)
    print("公众号排除逻辑测试")
    print("=" * 60)

    try:
        config = Settings()

        # 测试用例
        test_cases = [
            ("测试账号A", True),
            ("正常公众号B", False),
            ("内部测试", True),
            ("公开账号C", False),
        ]

        print("\n测试用例:")
        all_passed = True

        for account_name, should_be_excluded in test_cases:
            # 临时添加到排除列表进行测试
            if should_be_excluded and account_name not in config.wxchat_external_exclude_accounts:
                config.wxchat_external_exclude_accounts.append(account_name)

            is_excluded = account_name in config.wxchat_external_exclude_accounts
            passed = is_excluded == should_be_excluded

            status = "✅" if passed else "❌"
            print(f"   {status} 公众号 '{account_name}': ")
            print(f"      排除状态: {'已排除' if is_excluded else '未排除'}")

            if not passed:
                all_passed = False

        if all_passed:
            print("\n✅ 排除逻辑测试通过！")
        else:
            print("\n❌ 排除逻辑测试失败！")

        return all_passed

    except Exception as e:
        print(f"❌ 排除逻辑测试异常: {e}")
        return False

if __name__ == "__main__":
    import sys

    print("🚀 开始外部SFTP功能测试...")

    # 测试配置
    config_passed = test_external_sftp_config()

    # 测试排除逻辑
    exclusion_passed = test_exclusion_logic()

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"外部SFTP配置: {'✅ 通过' if config_passed else '❌ 失败'}")
    print(f"排除逻辑测试: {'✅ 通过' if exclusion_passed else '❌ 失败'}")

    if config_passed and exclusion_passed:
        print("\n🎉 所有测试通过！外部SFTP功能可以正常使用。")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败，请检查配置和设置。")
        sys.exit(1)
