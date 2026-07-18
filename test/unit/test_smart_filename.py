"""
测试智能文件名处理功能
"""
import pytest
import re
from src.utils.filename_handler import FilenameHandler


def test_smart_filename_extraction():
    """测试智能文件名提取功能"""

    # 测试用例：你提供的超长文件名
    long_path = "d:/f/901741041_Bobo_Huang123/Goldman Sachs-EM Weekly Fund Flows Monitor：Foreign selling continues driven by North Asia， while Southbound flows stay strong； HF de~grossing continues in July， while MFs rotate exposure to India in June； Korea Leveraged Flows Update-260717.pdf"

    handler = FilenameHandler()

    # 执行智能文件名处理
    smart_filename, original_filename, metadata = handler.generate_smart_filename(long_path)

    # 验证处理结果
    print(f"原始文件名长度: {len(original_filename)}")
    print(f"简化文件名: {smart_filename}")
    print(f"简化文件名长度: {len(smart_filename)}")
    print(f"缩短率: {((1 - len(smart_filename)/len(original_filename)) * 100):.1f}%")
    print(f"元数据: {metadata}")

    # 断言验证
    assert len(smart_filename) < 80, "简化文件名应该小于80字符"
    assert len(smart_filename) < len(original_filename), "简化文件名应该比原始文件名短"
    assert "901741041" in smart_filename, "应该包含用户ID"
    assert "260717" in smart_filename, "应该包含日期"
    assert smart_filename.endswith('.pdf'), "应该是PDF文件"

    # 🔥 验证唯一性：文件名中应该包含哈希
    assert re.search(r'_[a-f0-9]{6}\.pdf$', smart_filename), "应该包含6位哈希确保唯一性"


def test_user_id_extraction():
    """测试用户ID提取功能"""

    handler = FilenameHandler()

    # 测试用例
    test_cases = [
        ("d:/f/901741041_Bobo_Huang123/file.pdf", "901741041_Bobo_Huang123"),
        ("d:/f/123456789_TestUser/file.pdf", "123456789_TestUser"),
        ("d:/f/987654321/file.pdf", None),  # 没有用户ID
    ]

    for path, expected_user_id in test_cases:
        result = handler.extract_user_id_from_path(path)
        if expected_user_id:
            assert result == expected_user_id, f"应该提取到用户ID: {expected_user_id}"
        else:
            assert result == "" or result is None, f"不应该提取到用户ID: {path}"


def test_key_info_extraction():
    """测试关键信息提取功能"""

    handler = FilenameHandler()

    # 测试用例：你的文件名
    filename = "Goldman Sachs-EM Weekly Fund Flows Monitor：Foreign selling continues driven by North Asia， while Southbound flows stay strong； HF de~grossing continues in July， while MFs rotate exposure to India in June； Korea Leveraged Flows Update-260717.pdf"

    info = handler.extract_key_info(filename)

    print(f"提取的信息:")
    print(f"  日期: {info['date']}")
    print(f"  机构: {info['institution']}")
    print(f"  类型: {info['doc_type']}")
    print(f"  主题: {info['subject']}")
    print(f"  地区: {info['region']}")

    # 验证关键信息
    assert info['date'] == '260717', "应该提取到正确的日期"
    assert info['institution'] == 'Goldman_Sachs', "应该识别出Goldman Sachs"
    assert info['doc_type'] == 'Weekly', "应该是Weekly类型"
    assert info['subject'] == 'Fund_Flows', "应该是Fund Flows主题"
    assert info['region'] == 'EM', "应该是EM地区"


def test_filename_length_comparison():
    """测试文件名长度对比"""

    long_path = "d:/f/901741041_Bobo_Huang123/Goldman Sachs-EM Weekly Fund Flows Monitor：Foreign selling continues driven by North Asia， while Southbound flows stay strong； HF de~grossing continues in July， while MFs rotate exposure to India in June； Korea Leveraged Flows Update-260717.pdf"

    handler = FilenameHandler()
    smart_filename, original_filename, _ = handler.generate_smart_filename(long_path)

    # 验证缩短效果
    original_length = len(original_filename)
    smart_length = len(smart_filename)
    reduction_ratio = ((original_length - smart_length) / original_length) * 100

    print(f"文件名长度对比:")
    print(f"  原始: {original_length} 字符")
    print(f"  简化: {smart_length} 字符")
    print(f"  缩短: {original_length - smart_length} 字符")
    print(f"  缩短率: {reduction_ratio:.1f}%")

    # 断言：应该至少缩短50%
    assert reduction_ratio > 50, f"文件名应该至少缩短50%，实际缩短: {reduction_ratio:.1f}%"


def test_filename_uniqueness():
    """测试文件名唯一性保证"""

    handler = FilenameHandler()

    # 测试用例1：同一用户在同一天的不同文件
    path1 = "d:/f/901741041_Bobo_Huang123/Goldman Sachs-Fund Flows Report-260717.pdf"
    path2 = "d:/f/901741041_Bobo_Huang123/Goldman Sachs-Another Report-260717.pdf"

    smart1, _, metadata1 = handler.generate_smart_filename(path1)
    smart2, _, metadata2 = handler.generate_smart_filename(path2)

    print(f"唯一性测试 - 同一用户同一天不同文件:")
    print(f"  文件1: {smart1}")
    print(f"  文件2: {smart2}")
    print(f"  元数据1: {metadata1}")
    print(f"  元数据2: {metadata2}")

    # 验证：两个不同的文件应该生成不同的简化文件名
    assert smart1 != smart2, "不同的文件应该生成不同的简化文件名"

    # 测试用例2：提取不到有效信息的文件
    path3 = "d:/f/901741041_Bobo_Huang123/Random File Name.pdf"
    path4 = "d:/f/901741041_Bobo_Huang123/Another Random File.pdf"

    smart3, _, metadata3 = handler.generate_smart_filename(path3)
    smart4, _, metadata4 = handler.generate_smart_filename(path4)

    print(f"唯一性测试 - 随机文件名:")
    print(f"  文件3: {smart3}")
    print(f"  文件4: {smart4}")

    # 验证：即使没有有效信息，也应该生成不同的文件名
    assert smart3 != smart4, "即使没有有效信息，不同文件也应该生成不同的简化文件名"

    # 测试用例3：验证哈希格式
    import re
    hash_pattern = re.compile(r'_[a-f0-9]{6}\.pdf$')

    assert hash_pattern.search(smart1), "简化文件名应该包含6位哈希"
    assert hash_pattern.search(smart2), "简化文件名应该包含6位哈希"
    assert hash_pattern.search(smart3), "简化文件名应该包含6位哈希"
    assert hash_pattern.search(smart4), "简化文件名应该包含6位哈希"

    print(f"✅ 所有文件名都包含唯一性哈希")


if __name__ == "__main__":
    print("🧪 运行智能文件名处理测试...")
    print("=" * 60)

    try:
        test_smart_filename_extraction()
        print("\n✅ test_smart_filename_extraction 通过")

        test_user_id_extraction()
        print("✅ test_user_id_extraction 通过")

        test_key_info_extraction()
        print("✅ test_key_info_extraction 通过")

        test_filename_length_comparison()
        print("✅ test_filename_length_comparison 通过")

        test_filename_uniqueness()
        print("✅ test_filename_uniqueness 通过")

        print("\n🎉 所有测试通过！")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")