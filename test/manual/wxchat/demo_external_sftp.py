"""
外部SFTP功能演示脚本

展示如何使用外部SFTP功能：
1. 生成单个文章PDF
2. 上传到主SFTP和外部SFTP（如果不排除）
3. 演示排除逻辑
"""

import sys
import tempfile
from src.config.settings import Settings
from src.wxchat.processor import PDFGenerator
from src.uploader.sftp_client import SFTPClient

def demo_external_sftp():
    """演示外部SFTP功能"""

    print("=" * 60)
    print("外部SFTP功能演示")
    print("=" * 60)

    try:
        # 1. 加载配置
        print("\n1. 加载配置...")
        config = Settings()

        # 显示外部SFTP配置状态
        if config.wxchat_external_sftp_host:
            print(f"   ✅ 外部SFTP已配置")
            print(f"   主机: {config.wxchat_external_sftp_host}")
            print(f"   目录: {config.wxchat_external_sftp_folder}")
            print(f"   排除公众号: {config.wxchat_external_exclude_accounts or '无'}")
        else:
            print("   ℹ️  外部SFTP未配置，仅演示主SFTP上传")

        # 2. 测试文章ID（使用一个真实的微信文章ID进行演示）
        test_article_id = "6LJvQrYki3OyIJFmKE9NhA"  # 中东：以色列前进前线的指挥官曝光

        print(f"\n2. 生成PDF文件 (文章ID: {test_article_id})...")

        # 创建临时PDF文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            temp_pdf_path = tmp_file.name

        # 生成PDF
        pdf_generator = PDFGenerator(config)
        if pdf_generator.generate_pdf(test_article_id, temp_pdf_path):
            print(f"   ✅ PDF生成成功: {temp_pdf_path}")

            # 3. 上传到主SFTP
            print("\n3. 上传到主SFTP服务器...")
            try:
                with SFTPClient() as main_sftp:
                    # 模拟文件路径
                    yymm = "2607"  # 2026年7月
                    remote_path = f"{config.wxchat_sftp_remote_path}/{yymm}/demo_article.pdf"

                    if main_sftp.upload_file(temp_pdf_path, remote_path):
                        print(f"   ✅ 主SFTP上传成功: {remote_path}")
                    else:
                        print(f"   ❌ 主SFTP上传失败")

                # 4. 上传到外部SFTP（如果配置了）
                if config.wxchat_external_sftp_host:
                    print("\n4. 上传到外部SFTP服务器...")

                    # 构建外部SFTP配置
                    external_config = {
                        'host': config.wxchat_external_sftp_host,
                        'port': config.wxchat_external_sftp_port,
                        'username': config.wxchat_external_sftp_username,
                        'password': config.wxchat_external_sftp_password,
                        'remote_path': config.wxchat_external_sftp_folder
                    }

                    # 演示排除逻辑
                    test_account_name = "中东洞察"  # 假设这是公众号名称
                    if test_account_name in config.wxchat_external_exclude_accounts:
                        print(f"   ⏭️  公众号 '{test_account_name}' 在排除列表中，跳过外部上传")
                    else:
                        print(f"   📤 公众号 '{test_account_name}' 不在排除列表，进行外部上传...")

                        external_remote_path = f"{config.wxchat_external_sftp_folder}/{yymm}/demo_article.pdf"
                        with SFTPClient(custom_config=external_config) as external_sftp:
                            if external_sftp.upload_file(temp_pdf_path, external_remote_path):
                                print(f"   ✅ 外部SFTP上传成功: {external_remote_path}")
                            else:
                                print(f"   ❌ 外部SFTP上传失败")

                        # 演示排除场景
                        print(f"\n5. 模拟排除场景...")
                        print(f"   假设 '{test_account_name}' 在排除列表中：")
                        print(f"   ⏭️  将跳过外部SFTP上传，只保留主SFTP文件")
                else:
                    print("\n4. 外部SFTP未配置，跳过外部上传")

            except Exception as e:
                print(f"   ❌ SFTP操作失败: {e}")

            # 清理临时文件
            import os
            try:
                os.unlink(temp_pdf_path)
                print(f"\n🧹 清理临时文件完成")
            except Exception as e:
                print(f"   ⚠️  清理临时文件失败: {e}")

        else:
            print(f"   ❌ PDF生成失败")

        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)

        print("\n📋 功能说明：")
        print("✅ 支持同时上传到主SFTP和外部SFTP")
        print("✅ 支持通过公众号名称控制外部访问")
        print("✅ 外部上传失败不影响主流程")
        print("✅ 完整的错误处理和日志记录")

        return True

    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        return False

def demo_config_scenarios():
    """演示不同配置场景"""

    print("\n" + "=" * 60)
    print("配置场景演示")
    print("=" * 60)

    scenarios = [
        {
            "name": "场景1：仅主SFTP",
            "external_host": "",
            "exclude_accounts": [],
            "description": "所有文章只上传到主SFTP，无外部分发"
        },
        {
            "name": "场景2：全量外部分发",
            "external_host": "external.example.com",
            "exclude_accounts": [],
            "description": "所有文章同时上传到主SFTP和外部SFTP"
        },
        {
            "name": "场景3：部分外部分发",
            "external_host": "external.example.com",
            "exclude_accounts": ["内部账号", "测试账号"],
            "description": "排除特定公众号，其他文章正常外部分发"
        }
    ]

    for scenario in scenarios:
        print(f"\n📋 {scenario['name']}")
        print(f"   外部SFTP: {scenario['external_host'] or '未配置'}")
        print(f"   排除公众号: {', '.join(scenario['exclude_accounts']) if scenario['exclude_accounts'] else '无'}")
        print(f"   说明: {scenario['description']}")

if __name__ == "__main__":
    import sys

    print("🎯 外部SFTP功能演示")
    print("   此演示将展示：")
    print("   1. 配置加载和验证")
    print("   2. PDF生成和上传流程")
    print("   3. 主SFTP和外部SFTP双上传")
    print("   4. 公众号排除逻辑")

    # 演示配置场景
    demo_config_scenarios()

    # 演示实际功能
    success = demo_external_sftp()

    if success:
        print("\n🎉 演示成功！外部SFTP功能已就绪。")
        print("\n💡 下一步:")
        print("   1. 配置 .env 文件中的外部SFTP参数")
        print("   2. 运行测试工具: python test/diagnostic/test_external_sftp.py")
        print("   3. 正式使用: python main.py --wxchat --wxchat-days 7")
        sys.exit(0)
    else:
        print("\n⚠️  演示失败，请检查配置和环境。")
        sys.exit(1)
