#!/usr/bin/env python3
"""
分享链接转存功能问题诊断和修复工具

发现的问题:
1. save_share_link 方法中的逻辑错误
2. BaiduPCS-Go transfer 命令的限制
3. Cookie 配置可能有问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def analyze_current_logic():
    """分析当前的转存逻辑"""
    print("=" * 60)
    print("当前 save_share_link 逻辑分析")
    print("=" * 60)

    print("\n当前代码逻辑:")
    print("""
    def save_share_link(self, share_link: str, code: str, folder_name: str) -> bool:
        if folder_name:
            # 切换到根目录
            self._run_command(['cd', '/'])
            # 删除可能存在的同名目录
            self.delete_directory(folder_name)

        # 转存分享链接到当前目录（根目录）
        command = ['transfer', clean_link, code]
        result = self._run_command(command)
    """)

    print("\n问题分析:")
    print("1. BaiduPCS-Go 的 transfer 命令只能转存到当前目录")
    print("2. 不能直接指定转存后的目标目录名")
    print("3. 转存后的目录名由分享链接的原始目录名决定")
    print("4. 代码中删除同名目录的逻辑无效")

    print("\n解决方案:")
    print("方案A: 转存后重命名目录")
    print("  1. 转存到根目录")
    print("  2. 获取转存后的目录名")
    print("  3. 重命名为目标目录名")

    print("\n方案B: 使用 mv 命令移动到目标位置")
    print("  1. 转存到根目录")
    print("  2. 移动到目标目录")

    print("\n方案C: 接受原始目录名")
    print("  1. 直接转存，不指定目标目录名")
    print("  2. 使用实际的转存目录名进行后续操作")

def test_transfer_with_real_link():
    """测试实际的转存操作"""
    print("\n" + "=" * 60)
    print("实际转存测试")
    print("=" * 60)

    print("\n注意: 这将进行实际的转存操作")
    print("建议使用一个测试链接来验证功能")

    # 这里可以添加实际的测试代码
    print("\n测试步骤:")
    print("1. 切换到根目录: cd /")
    print("2. 执行转存: transfer <分享链接> <提取码>")
    print("3. 列出根目录内容: ls /")
    print("4. 检查转存的目录名")

def propose_fix():
    """提出修复方案"""
    print("\n" + "=" * 60)
    print("推荐修复方案")
    print("=" * 60)

    print("""
    修复后的 save_share_link 方法:

    def save_share_link(self, share_link: str, code: str, folder_name: str = None) -> Dict[str, any]:
        \"\"\"
        转存分享链接到网盘目录

        Args:
            share_link: 分享链接
            code: 提取码
            folder_name: 目标目录名（可选，如果不指定则使用原始目录名）

        Returns:
            包含 success 和 actual_folder_name 的字典
        \"\"\"
        try:
            # 1. 切换到根目录
            self._run_command(['cd', '/'])

            # 2. 获取转存前的目录列表
            before_list = self._run_command(['ls', '/'])

            # 3. 执行转存命令
            clean_link = share_link.split('?pwd=')[0]
            if code and code.strip():
                command = ['transfer', clean_link, code]
            else:
                command = ['transfer', clean_link]

            result = self._run_command(command)

            if result['returncode'] != 0:
                logger.error(f"Save share link failed: {result['stderr']}")
                return {'success': False, 'actual_folder_name': None}

            # 4. 获取转存后的目录列表
            after_list = self._run_command(['ls', '/'])

            # 5. 比较差异，找出新转存的目录
            new_folders = self._find_new_folders(before_list, after_list)

            if not new_folders:
                logger.error("No new folder found after transfer")
                return {'success': False, 'actual_folder_name': None}

            actual_folder = new_folders[0]
            logger.info(f"Share link saved to actual folder: /{actual_folder}")

            # 6. 如果指定了目标目录名且与实际目录名不同，进行重命名
            if folder_name and folder_name != actual_folder:
                logger.info(f"Renaming folder from {actual_folder} to {folder_name}")
                rename_result = self._run_command(['mv', f'/{actual_folder}', f'/{folder_name}'])
                if rename_result['returncode'] == 0:
                    logger.info(f"Folder renamed successfully to /{folder_name}")
                    return {'success': True, 'actual_folder_name': folder_name}
                else:
                    logger.warning(f"Folder rename failed, using actual name: {actual_folder}")
                    return {'success': True, 'actual_folder_name': actual_folder}
            else:
                return {'success': True, 'actual_folder_name': actual_folder}

        except Exception as e:
            logger.error(f"Save share link exception: {e}")
            return {'success': False, 'actual_folder_name': None}
    """)

def main():
    """主函数"""
    print("分享链接转存功能诊断工具")
    print("=" * 60)

    analyze_current_logic()
    test_transfer_with_real_link()
    propose_fix()

    print("\n" + "=" * 60)
    print("下一步建议:")
    print("=" * 60)
    print("""
1. 备份当前的 baidu_client.py 文件
2. 应用推荐的修复方案
3. 使用测试链接验证功能
4. 如果成功，更新相关调用代码
    """)

if __name__ == '__main__':
    main()
