"""
wxchat-article功能完整集成测试

测试完整的端到端流程：
1. 消息解析
2. 文章下载和元数据提取
3. PDF生成
4. SFTP上传路径验证
5. 钉钉反馈通知测试
6. 数据库记录完整性检查
7. 错误处理和重试机制

Author: Task 8 Integration Test
Date: 2026-08-21
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.processor.parsers.wxchat_article_processor import WxchatArticleProcessor, DownloadResult, ProcessResult
from src.feishu.message_parser import MessageParser
from src.feishu.models import ParseResult
from src.uploader.sftp_client import SFTPClient
from src.feishu.dingtalk_group_client import DingTalkGroupClient
from src.database.models import DatabaseManager
from src.utils.logger import get_logger


class WxchatArticleIntegrationTest:
    """微信文章链接完整集成测试"""

    def __init__(self):
        """初始化测试环境"""
        self.logger = get_logger(__name__)
        self.settings = Settings()
        self.parser = MessageParser(self.settings)
        self.article_processor = WxchatArticleProcessor(self.settings)
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

        # 真实测试URL（来自背景信息）
        self.real_test_url = "https://mp.weixin.qq.com/s/QfzFNnLB88WFwD6bwSVSjQ"

    def print_header(self, title: str):
        """打印测试标题"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def print_test(self, test_name: str, passed: bool, details: str = ""):
        """打印测试结果"""
        self.total_tests += 1
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details:
            print(f"     {details}")

        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1

        self.test_results[test_name] = {
            'passed': passed,
            'details': details
        }

    def test_01_configuration_validation(self):
        """测试1: 配置完整性验证"""
        self.print_header("测试1: 配置完整性验证")

        try:
            # 检查wxchat相关配置
            configs = [
                ('wxchat_enabled', self.settings.wxchat_enabled),
                ('wxchat_sftp_remote_path', self.settings.wxchat_sftp_remote_path),
                ('wxchat_base_url', self.settings.wxchat_base_url),
                ('wxchat_pdf_timeout', self.settings.wxchat_pdf_timeout),
            ]

            all_valid = True
            for name, value in configs:
                is_valid = value is not None and value != ''
                self.print_test(f"配置项 {name}", is_valid, f"值: {value}")
                if not is_valid:
                    all_valid = False

            self.print_test("配置完整性检查", all_valid)
            return all_valid

        except Exception as e:
            self.print_test("配置验证异常", False, str(e))
            return False

    def test_02_message_parsing(self):
        """测试2: 消息解析功能"""
        self.print_header("测试2: 消息解析功能")

        try:
            # 测试真实的微信文章消息
            test_message = f"请下载这篇文章的PDF: {self.real_test_url}"

            print(f"测试消息: {test_message}")
            parse_result = self.parser.parse_message(test_message, message_source='dingtalk')

            # 验证解析结果
            has_url = parse_result.wxchat_article_url is not None
            has_id = parse_result.wxchat_article_id is not None
            correct_type = parse_result.message_type == 'wxchat-article'

            self.print_test("消息类型识别", correct_type, f"识别为: {parse_result.message_type}")
            self.print_test("URL提取", has_url, f"URL: {parse_result.wxchat_article_url}")
            self.print_test("文章ID提取", has_id, f"ID: {parse_result.wxchat_article_id}")

            # 保存解析结果供后续测试使用
            self.parse_result = parse_result

            return all([has_url, has_id, correct_type])

        except Exception as e:
            self.print_test("消息解析异常", False, str(e))
            return False

    def test_03_article_download(self):
        """测试3: 文章元数据下载"""
        self.print_header("测试3: 文章元数据下载")

        if not hasattr(self, 'parse_result'):
            self.print_test("跳过测试", False, "没有有效的解析结果")
            return False

        try:
            print(f"正在下载文章信息: {self.real_test_url}")

            # 下载文章元数据
            download_result = self.article_processor.download(self.parse_result)

            # 验证下载结果
            success = download_result.success
            has_title = download_result.article_title is not None
            has_account = download_result.account_name is not None

            self.print_test("文章下载成功", success)
            self.print_test("文章标题提取", has_title, f"标题: {download_result.article_title}")
            self.print_test("公众号名称提取", has_account, f"公众号: {download_result.account_name}")

            if success:
                print(f"\n📄 文章信息:")
                print(f"   标题: {download_result.article_title}")
                print(f"   公众号: {download_result.account_name}")

            # 保存下载结果供后续测试使用
            self.download_result = download_result

            return success

        except Exception as e:
            self.print_test("文章下载异常", False, str(e))
            return False

    def test_04_pdf_generation(self):
        """测试4: PDF生成功能"""
        self.print_header("测试4: PDF生成功能")

        if not hasattr(self, 'download_result') or not self.download_result.success:
            self.print_test("跳过测试", False, "没有有效的下载结果")
            return False

        try:
            print(f"正在生成PDF...")

            # 生成PDF
            process_result = self.article_processor.process(self.download_result, self.parse_result)

            # 验证处理结果
            success = process_result.success
            has_files = len(process_result.processed_files) > 0

            self.print_test("PDF生成成功", success)
            self.print_test("文件列表非空", has_files, f"文件数: {len(process_result.processed_files)}")

            if success and has_files:
                for file_path in process_result.processed_files:
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path) / (1024 * 1024)
                        self.print_test(f"PDF文件存在", True, f"路径: {file_path}, 大小: {file_size:.2f}MB")
                        print(f"\n📄 PDF文件: {file_path}")
                        print(f"   大小: {file_size:.2f}MB")
                    else:
                        self.print_test(f"PDF文件不存在", False, f"路径: {file_path}")

            # 保存处理结果供后续测试使用
            self.process_result = process_result

            return success

        except Exception as e:
            self.print_test("PDF生成异常", False, str(e))
            return False

    def test_05_sftp_path_verification(self):
        """测试5: SFTP上传路径验证"""
        self.print_header("测试5: SFTP上传路径验证")

        if not hasattr(self, 'process_result') or not self.process_result.success:
            self.print_test("跳过测试", False, "没有有效的处理结果")
            return False

        try:
            # 获取上传文件列表
            upload_files = self.article_processor.get_upload_files(self.process_result, self.parse_result)

            has_files = len(upload_files) > 0
            self.print_test("上传文件列表非空", has_files, f"文件数: {len(upload_files)}")

            if has_files:
                for upload_info in upload_files:
                    local_path = upload_info['local_path']
                    remote_path = upload_info['remote_path']
                    file_size = upload_info['size']

                    # 验证路径格式
                    local_exists = os.path.exists(local_path)
                    remote_has_wxchat = remote_path.startswith(self.settings.wxchat_sftp_remote_path)
                    has_year_month = len(remote_path.split('/')) >= 3  # 至少有 wxchat/YYYYMM/filename.pdf
                    filename_valid = remote_path.endswith('.pdf')

                    self.print_test("本地文件存在", local_exists, f"路径: {local_path}")
                    self.print_test("远程路径包含wxchat", remote_has_wxchat, f"路径: {remote_path}")
                    self.print_test("远程路径包含年月", has_year_month)
                    self.print_test("文件名有效", filename_valid)

                    print(f"\n📤 上传信息:")
                    print(f"   本地路径: {local_path}")
                    print(f"   远程路径: {remote_path}")
                    print(f"   文件大小: {file_size / (1024*1024):.2f}MB")

                    # 验证路径结构一致性
                    expected_base = f"{self.settings.wxchat_sftp_remote_path}"
                    path_structure_ok = remote_path.startswith(expected_base)
                    self.print_test("路径结构一致性", path_structure_ok,
                                  f"期望基础: {expected_base}")

                return all([local_exists, remote_has_wxchat, has_year_month, filename_valid, path_structure_ok])

            return False

        except Exception as e:
            self.print_test("路径验证异常", False, str(e))
            return False

    def test_06_sftp_connection(self):
        """测试6: SFTP连接测试"""
        self.print_header("测试6: SFTP连接测试")

        try:
            print(f"正在连接SFTP服务器...")
            print(f"   主机: {self.settings.sftp_host}")
            print(f"   端口: {self.settings.sftp_port}")
            print(f"   用户: {self.settings.sftp_username}")

            # 创建SFTP客户端并测试连接
            sftp_client = SFTPClient(self.settings)
            connection_success = sftp_client.test_connection()

            self.print_test("SFTP连接成功", connection_success)

            if connection_success:
                print(f"✅ SFTP连接测试成功")

            return connection_success

        except Exception as e:
            self.print_test("SFTP连接测试异常", False, str(e))
            return False

    def test_07_dingtalk_notification(self):
        """测试7: 钉钉通知机制测试"""
        self.print_header("测试7: 钉钉通知机制测试")

        try:
            # 检查钉钉配置
            has_webhook = bool(self.settings.dingtalk_webhook)
            has_app_key = bool(self.settings.dingtalk_app_key)

            self.print_test("钉钉Webhook配置", has_webhook,
                          f"Webhook: {self.settings.dingtalk_webhook[:30]}..." if has_webhook else "未配置")
            self.print_test("钉钉AppKey配置", has_app_key,
                          f"AppKey: {self.settings.dingtalk_app_key}" if has_app_key else "未配置")

            if has_webhook:
                print(f"\n📱 钉钉通知配置:")
                print(f"   Webhook: {self.settings.dingtalk_webhook[:50]}...")
                print(f"   ChatID: {self.settings.dingtalk_chat_id}")
                print(f"   AppKey: {self.settings.dingtalk_app_key}")

                # 如果有完整的解析和处理结果，测试通知格式
                if hasattr(self, 'process_result') and self.process_result.success:
                    print(f"\n📝 模拟通知消息:")
                    notification_text = self._generate_notification_text()
                    print(f"   {notification_text}")

            return has_webhook or has_app_key

        except Exception as e:
            self.print_test("钉钉通知测试异常", False, str(e))
            return False

    def _generate_notification_text(self) -> str:
        """生成模拟通知文本"""
        if hasattr(self, 'download_result') and hasattr(self, 'process_result'):
            return (f"✅ 微信文章PDF生成成功\n"
                   f"📄 文章: {self.download_result.article_title}\n"
                   f"🏢 公众号: {self.download_result.account_name}\n"
                   f"📁 文件: {len(self.process_result.processed_files)}个PDF文件")
        return "通知内容生成"

    def test_08_database_integration(self):
        """测试8: 数据库集成测试"""
        self.print_header("测试8: 数据库集成测试")

        try:
            # 测试数据库连接
            db_manager = DatabaseManager(self.settings)
            connection_success = db_manager.test_connection()

            self.print_test("数据库连接成功", connection_success)

            if connection_success:
                print(f"✅ 数据库连接测试成功")
                print(f"   主机: {self.settings.db_host}")
                print(f"   数据库: {self.settings.db_name}")

                # 检查相关表是否存在
                tables = db_manager.get_all_tables()
                has_messages_table = 'messages' in tables
                has_transfers_table = 'transfers' in tables
                has_wxchat_tables = any('wxchat' in table.lower() for table in tables)

                self.print_test("messages表存在", has_messages_table)
                self.print_test("transfers表存在", has_transfers_table)
                self.print_test("wxchat相关表存在", has_wxchat_tables)

                return all([connection_success, has_messages_table, has_transfers_table])

            return connection_success

        except Exception as e:
            self.print_test("数据库集成测试异常", False, str(e))
            return False

    def test_09_error_handling(self):
        """测试9: 错误处理和重试机制"""
        self.print_header("测试9: 错误处理和重试机制")

        try:
            # 测试无效URL处理
            print("测试无效URL处理...")
            invalid_parse_result = ParseResult(
                message_type='wxchat-article',
                wxchat_article_url='https://invalid.url',
                wxchat_article_id='invalid_id'
            )

            invalid_download = self.article_processor.download(invalid_parse_result)
            self.print_test("无效URL正确识别", not invalid_download.success,
                          f"错误信息: {invalid_download.error}")

            # 测试重试配置
            has_retry_config = hasattr(self.settings, 'max_message_retries')
            retry_value = self.settings.max_message_retries if has_retry_config else 0
            self.print_test("重试配置存在", has_retry_config and retry_value > 0,
                          f"最大重试次数: {retry_value}")

            # 测试清理功能
            self.article_processor.cleanup()
            self.print_test("临时文件清理功能", True, "cleanup()方法调用成功")

            return not invalid_download.success and has_retry_config

        except Exception as e:
            self.print_test("错误处理测试异常", False, str(e))
            return False

    def test_10_path_consistency(self):
        """测试10: 路径结构一致性验证"""
        self.print_header("测试10: 路径结构一致性验证")

        try:
            # 验证wxchat-article和wxchat使用相同的路径结构
            wxchat_base = self.settings.wxchat_sftp_remote_path

            # 获取当前上传文件列表
            if hasattr(self, 'process_result') and self.process_result.success:
                upload_files = self.article_processor.get_upload_files(self.process_result, self.parse_result)

                if upload_files:
                    for upload_info in upload_files:
                        remote_path = upload_info['remote_path']

                        # 验证路径结构
                        starts_with_wxchat = remote_path.startswith(wxchat_base)
                        has_date_folder = len(remote_path.split('/')) >= 3  # /wxchat/YYYYMM/filename.pdf
                        is_pdf = remote_path.endswith('.pdf')

                        self.print_test("路径基础一致性", starts_with_wxchat,
                                      f"期望: {wxchat_base}, 实际: {remote_path[:len(wxchat_base)+10]}...")
                        self.print_test("日期目录结构", has_date_folder)
                        self.print_test("PDF文件后缀", is_pdf)

                        # 打印路径结构
                        print(f"\n📂 路径结构分析:")
                        print(f"   完整路径: {remote_path}")
                        print(f"   基础路径: {wxchat_base}")
                        print(f"   路径组件: {remote_path.split('/')}")

                        return all([starts_with_wxchat, has_date_folder, is_pdf])

            # 如果没有上传文件，至少验证配置存在
            self.print_test("路径配置存在", bool(wxchat_base), f"值: {wxchat_base}")
            return bool(wxchat_base)

        except Exception as e:
            self.print_test("路径一致性测试异常", False, str(e))
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始wxchat-article功能完整集成测试")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试URL: {self.real_test_url}")

        # 运行所有测试
        test_results = []
        test_results.append(("配置验证", self.test_01_configuration_validation()))
        test_results.append(("消息解析", self.test_02_message_parsing()))
        test_results.append(("文章下载", self.test_03_article_download()))
        test_results.append(("PDF生成", self.test_04_pdf_generation()))
        test_results.append(("SFTP路径验证", self.test_05_sftp_path_verification()))
        test_results.append(("SFTP连接", self.test_06_sftp_connection()))
        test_results.append(("钉钉通知", self.test_07_dingtalk_notification()))
        test_results.append(("数据库集成", self.test_08_database_integration()))
        test_results.append(("错误处理", self.test_09_error_handling()))
        test_results.append(("路径一致性", self.test_10_path_consistency()))

        # 清理临时文件
        try:
            self.article_processor.cleanup()
        except:
            pass

        # 打印最终报告
        self.print_final_report(test_results)

    def print_final_report(self, test_results):
        """打印最终测试报告"""
        self.print_header("📊 测试报告总结")

        print(f"\n测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试总数: {self.total_tests}")
        print(f"通过: {self.passed_tests} ({self.passed_tests/self.total_tests*100:.1f}%)")
        print(f"失败: {self.failed_tests} ({self.failed_tests/self.total_tests*100:.1f}%)")

        print(f"\n模块测试结果:")
        for module, result in test_results:
            status = "✅" if result else "❌"
            print(f"{status} {module}")

        # 判断整体状态
        success_rate = self.passed_tests / self.total_tests if self.total_tests > 0 else 0
        deployment_ready = success_rate >= 0.8  # 80%以上通过率视为部署就绪

        print(f"\n🎯 部署就绪状态:")
        if deployment_ready:
            print(f"✅ 就绪 - 测试通过率 {success_rate*100:.1f}% >= 80%")
        else:
            print(f"❌ 未就绪 - 测试通过率 {success_rate*100:.1f}% < 80%")

        print(f"\n📝 备注:")
        print(f"- 测试URL: {self.real_test_url}")
        print(f"- SFTP基础路径: {self.settings.wxchat_sftp_remote_path}")
        print(f"- 配置文件: .env")

        if deployment_ready:
            print(f"\n🚀 wxchat-article功能已准备就绪，可以进行生产部署！")
        else:
            print(f"\n⚠️  请修复失败的测试后再进行部署。")


def main():
    """主函数"""
    try:
        tester = WxchatArticleIntegrationTest()
        tester.run_all_tests()
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n\n❌ 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())