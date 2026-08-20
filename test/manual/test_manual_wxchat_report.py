#!/usr/bin/env python
"""
手动测试微信文章处理报告发送功能

使用方法：
1. 确保 .env 中配置了 DINGTALK_WEBHOOK
2. 运行此脚本：python test_manual_wxchat_report.py
3. 检查钉钉群是否收到测试报告

注意：实际使用时，只在有新增文章或有失败文章时才发送报告
"""

import sys
import os
from datetime import datetime
from datetime import timedelta

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config.settings import Settings
from src.wxchat.models import ProcessResult
from src.notification.dingtalk_notifier import DingtalkNotifier


def create_test_result():
    """创建测试用的处理结果"""
    result = ProcessResult()
    result.total_articles = 25
    result.processed_articles = 20
    result.failed_articles = 3
    result.skipped_articles = 2
    result.start_time = datetime.now() - timedelta(minutes=5, seconds=30)
    result.end_time = datetime.now()
    result.errors = [
        "PDF生成失败: article_id_12345",
        "SFTP上传失败: article_id_67890",
        "外部SFTP连接超时: article_id_54321"
    ]
    return result


def generate_report_content(result: ProcessResult) -> tuple:
    """生成报告内容（标题和内容）"""

    # 构建报告消息
    report_title = "📊 微信文章处理报告"
    report_content = f"""## 微信文章处理完成报告

### 📈 处理统计
- **总计文章**: {result.total_articles} 篇
- **✅ 成功处理**: {result.processed_articles} 篇
- **❌ 失败文章**: {result.failed_articles} 篇
- **⏭️ 跳过文章**: {result.skipped_articles} 篇

### ⏱️ 处理时间
"""

    if result.start_time and result.end_time:
        duration = (result.end_time - result.start_time).total_seconds()
        start_time_str = result.start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = result.end_time.strftime('%Y-%m-%d %H:%M:%S')
        report_content += f"- **开始时间**: {start_time_str}\n"
        report_content += f"- **结束时间**: {end_time_str}\n"
        report_content += f"- **处理耗时**: {duration:.2f} 秒\n\n"

    # 添加错误信息（如果有）
    if result.errors:
        total_errors = len(result.errors)
        display_count = min(5, total_errors)
        report_content += f"### ⚠️ 错误信息 ({total_errors} 个)\n"
        for error in result.errors[:display_count]:
            report_content += f"- {error}\n"
        if total_errors > display_count:
            report_content += f"- ... 还有 {total_errors - display_count} 个错误未显示\n"
        report_content += "\n"

    # 添加状态总结
    if result.failed_articles == 0:
        report_content += "### 🎉 处理完成\n所有文章处理成功，无失败！"
    else:
        success_rate = (result.processed_articles / result.total_articles * 100) if result.total_articles > 0 else 0
        report_content += f"### 📋 处理完成\n成功率: {success_rate:.1f}%"

    return report_title, report_content


def main():
    """主测试函数"""
    print("=" * 60)
    print("微信文章处理报告发送测试")
    print("=" * 60)

    try:
        # 加载配置
        print("\n1. 加载配置...")
        settings = Settings()

        if not settings.dingtalk_webhook:
            print("❌ 错误: DINGTALK_WEBHOOK 未配置")
            print("请在 .env 文件中设置 DINGTALK_WEBHOOK")
            return 1

        print(f"✅ 配置加载成功")
        print(f"   Webhook: {settings.dingtalk_webhook[:50]}...")

        # 创建测试结果
        print("\n2. 创建测试数据...")
        result = create_test_result()
        print(f"✅ 测试数据创建成功")
        print(f"   总计文章: {result.total_articles} 篇")
        print(f"   成功处理: {result.processed_articles} 篇")
        print(f"   失败文章: {result.failed_articles} 篇")
        print(f"   跳过文章: {result.skipped_articles} 篇")

        # 生成报告内容
        print("\n3. 生成报告内容...")
        report_title, report_content = generate_report_content(result)
        print(f"✅ 报告生成成功")
        print(f"   标题: {report_title}")
        print(f"   内容预览: {report_content[:100]}...")

        # 发送报告
        print("\n4. 发送报告到钉钉群...")
        notifier = DingtalkNotifier(settings)

        if notifier.send_notification(report_title, report_content):
            print("✅ 报告发送成功！")
            print("\n请检查钉钉群是否收到测试报告")
            print("\n报告内容：")
            print("-" * 60)
            print(report_content)
            print("-" * 60)
            return 0
        else:
            print("❌ 报告发送失败")
            print("请检查：")
            print("1. Webhook地址是否正确")
            print("2. 网络连接是否正常")
            print("3. 钉钉机器人配置是否正确")
            return 1

    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    print("\n" + "=" * 60)
    print(f"测试{'成功' if exit_code == 0 else '失败'}")
    print("=" * 60)
    exit(exit_code)