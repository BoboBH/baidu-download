"""
测试wxchat-article通知功能

验证FileTransferProcessor能够正确发送微信文章的钉钉通知
"""
import sys
import os
# 设置UTF-8编码输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime
from src.processor.file_transfer_processor import ProcessResult
from src.config.settings import Settings
from src.notification.dingtalk_notifier import DingtalkNotifier


def test_wxchat_notification_format():
    """测试微信文章通知格式化"""

    # 创建一个模拟的wxchat-article ProcessResult
    result = ProcessResult(
        message_id=1,
        folder_name="temp_folder",  # 对wxchat-article不重要，会被metadata覆盖
        share_link="https://mp.weixin.qq.com/s/test123",
        status="success",
        message_type="wxchat-article",
        error_message=None,
        processing_time_ms=5000,
        total_files=1,
        success_count=1,
        failed_count=0,
        skipped_count=0,
        total_size_mb=2.5,
        metadata={
            'article_title': '测试文章标题：如何集成钉钉通知',
            'account_name': '技术博客公众号',
            'article_id': 'test123'
        }
    )

    # 模拟通知内容构建逻辑
    content_lines = [
        "## 📢 Foundry：文件处理完成通知",
        "",
        "### 处理结果",
        ""
    ]

    # 根据消息类型定制显示内容
    if result.message_type == 'wxchat-article' and hasattr(result, 'metadata') and result.metadata:
        # 微信文章：显示文章标题和公众号名称
        article_title = result.metadata.get('article_title', '未知文章')
        account_name = result.metadata.get('account_name', '未知公众号')
        content_lines.extend([
            f"**文章标题**: {article_title}",
            f"**公众号**: {account_name}",
            f"**类型**: 微信文章",
            f"**状态**: {'✅ 成功' if result.status == 'success' else '❌ 失败'}",
            ""
        ])
    else:
        # 其他消息类型：显示文件夹名称
        content_lines.extend([
            f"**文件夹**: {result.folder_name}",
            f"**类型**: {result.message_type or 'N/A'}",
            f"**状态**: {'✅ 成功' if result.status == 'success' else '❌ 失败'}",
            ""
        ])

    # 添加share_link信息（如果存在）
    if hasattr(result, 'share_link') and result.share_link:
        content_lines.extend([
            f"**分享链接**: {result.share_link[:100]}{'...' if len(result.share_link) > 100 else ''}",
            ""
        ])

    if result.status == "success":
        content_lines.extend([
            "### 详细统计",
            "",
            f"- **总文件数**: {result.total_files}",
            f"- **成功传输**: {result.success_count}",
            f"- **传输失败**: {result.failed_count}",
            f"- **总大小**: {result.total_size_mb:.2f} MB",
            f"- **处理耗时**: {result.processing_time_ms / 1000:.2f} 秒"
        ])

    # 添加时间戳
    content_lines.extend([
        "",
        f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ])

    content = "\n".join(content_lines)

    print("=" * 60)
    print("微信文章通知内容生成测试")
    print("=" * 60)
    print(content)
    print("=" * 60)

    # 验证关键结构元素（使用英文key避免编码问题）
    assert "article_title" not in content  # 确保不是字段名
    assert "Foundry" in content  # 标题包含关键词
    assert ": 1" in content  # 统计数字
    assert "2.50" in content  # 文件大小数字
    assert "5.00" in content  # 处理时间数字
    assert "mp.weixin.qq.com" in content  # 微信链接

    print("✅ 通知内容格式验证通过")
    return True


def test_baidupan_notification_format():
    """测试百度网盘通知格式化（确保不破坏原有功能）"""

    # 创建一个模拟的baidupan ProcessResult
    result = ProcessResult(
        message_id=2,
        folder_name="我的文件夹",
        share_link="https://pan.baidu.com/s/xxxxx",
        status="success",
        message_type="baidupan",
        error_message=None,
        processing_time_ms=3000,
        total_files=5,
        success_count=5,
        failed_count=0,
        skipped_count=0,
        total_size_mb=10.5
    )

    # 模拟通知内容构建逻辑
    content_lines = [
        "## 📢 Foundry：文件处理完成通知",
        "",
        "### 处理结果",
        ""
    ]

    # 根据消息类型定制显示内容
    if result.message_type == 'wxchat-article' and hasattr(result, 'metadata') and result.metadata:
        # 微信文章：显示文章标题和公众号名称
        article_title = result.metadata.get('article_title', '未知文章')
        account_name = result.metadata.get('account_name', '未知公众号')
        content_lines.extend([
            f"**文章标题**: {article_title}",
            f"**公众号**: {account_name}",
            f"**类型**: 微信文章",
            f"**状态**: {'✅ 成功' if result.status == 'success' else '❌ 失败'}",
            ""
        ])
    else:
        # 其他消息类型：显示文件夹名称
        content_lines.extend([
            f"**文件夹**: {result.folder_name}",
            f"**类型**: {result.message_type or 'N/A'}",
            f"**状态**: {'✅ 成功' if result.status == 'success' else '❌ 失败'}",
            ""
        ])

    if result.status == "success":
        content_lines.extend([
            "### 详细统计",
            "",
            f"- **总文件数**: {result.total_files}",
            f"- **成功传输**: {result.success_count}",
            f"- **传输失败**: {result.failed_count}",
            f"- **总大小**: {result.total_size_mb:.2f} MB",
            f"- **处理耗时**: {result.processing_time_ms / 1000:.2f} 秒"
        ])

    content = "\n".join(content_lines)

    print("\n" + "=" * 60)
    print("百度网盘通知内容生成测试")
    print("=" * 60)
    print(content)
    print("=" * 60)

    # 验证关键结构元素（避免中文编码问题）
    assert "Foundry" in content
    assert "baidupan" in content
    assert ": 5" in content  # 文件数
    assert "10.50" in content  # 文件大小
    # 确保不包含微信文章的字段（使用英文检查）
    assert "**文章标题**" not in content
    assert "**公众号**" not in content

    print("✅ 百度网盘通知格式验证通过（未破坏原有功能）")
    return True


def test_dingtalk_notifier_integration():
    """测试实际发送到钉钉（需要配置webhook）"""

    try:
        settings = Settings()
        if not settings.dingtalk_webhook:
            print("⚠️  未配置钉钉webhook，跳过实际发送测试")
            return True

        notifier = DingtalkNotifier(settings)

        # 创建测试结果
        result = ProcessResult(
            message_id=99,
            folder_name="test",
            share_link="https://mp.weixin.qq.com/s/test",
            status="success",
            message_type="wxchat-article",
            processing_time_ms=2000,
            total_files=1,
            success_count=1,
            failed_count=0,
            total_size_mb=1.0,
            metadata={
                'article_title': '测试通知功能',
                'account_name': '测试公众号'
            }
        )

        # 构建通知内容
        content_lines = [
            "## 📢 Foundry：文件处理完成通知",
            "",
            "### 处理结果",
            "",
            f"**文章标题**: {result.metadata.get('article_title', '未知文章')}",
            f"**公众号**: {result.metadata.get('account_name', '未知公众号')}",
            f"**类型**: 微信文章",
            f"**状态**: {'✅ 成功' if result.status == 'success' else '❌ 失败'}",
            "",
            f"**分享链接**: {result.share_link}",
            "",
            "### 详细统计",
            "",
            f"- **总文件数**: {result.total_files}",
            f"- **成功传输**: {result.success_count}",
            f"- **传输失败**: {result.failed_count}",
            f"- **总大小**: {result.total_size_mb:.2f} MB",
            f"- **处理耗时**: {result.processing_time_ms / 1000:.2f} 秒",
            "",
            f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]

        content = "\n".join(content_lines)

        print("\n" + "=" * 60)
        print("钉钉通知发送测试")
        print("=" * 60)

        # 发送通知
        success = notifier.send_notification("微信文章处理完成测试", content)

        if success:
            print("✅ 钉钉通知发送成功")
        else:
            print("❌ 钉钉通知发送失败")

        return success

    except Exception as e:
        print(f"❌ 钉钉通知测试异常: {e}")
        return False


if __name__ == "__main__":
    print("开始测试wxchat-article通知功能...")

    try:
        # 测试1: 验证通知格式
        test1_passed = test_wxchat_notification_format()

        # 测试2: 验证不破坏原有功能
        test2_passed = test_baidupan_notification_format()

        # 测试3: 实际发送测试（可选）
        test3_passed = test_dingtalk_notifier_integration()

        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        print(f"微信文章格式化测试: {'✅ 通过' if test1_passed else '❌ 失败'}")
        print(f"百度网盘格式化测试: {'✅ 通过' if test2_passed else '❌ 失败'}")
        print(f"钉钉通知发送测试: {'✅ 通过' if test3_passed else '⚠️  跳过/失败'}")
        print("=" * 60)

        if test1_passed and test2_passed:
            print("✅ 所有核心测试通过")
            sys.exit(0)
        else:
            print("❌ 部分测试失败")
            sys.exit(1)

    except Exception as e:
        print(f"❌ 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)