import subprocess
import os
import re
import uuid
import time
from pathlib import Path
from typing import List, Dict, Optional
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class BaiduClient:
    """百度网盘客户端，封装BaiduPCS-Go命令行工具"""

    def __init__(self):
        """初始化客户端"""
        self.settings = Settings()
        self.baidupcs_path = self.settings.baidupcs_go_path
        self.cookies_path = self.settings.baidu_cookies_path
        self.temp_dir = self.settings.temp_dir

        # 验证BaiduPCS-Go是否存在
        if not Path(self.baidupcs_path).exists():
            raise FileNotFoundError(f"BaiduPCS-Go not found: {self.baidupcs_path}")

        logger.info(f"BaiduClient initialized with BaiduPCS-Go: {self.baidupcs_path}")

    def _run_command(self, args: List[str]) -> Dict[str, any]:
        """
        运行BaiduPCS-Go命令

        Args:
            args: 命令参数列表

        Returns:
            包含stdout, stderr, returncode的字典
        """
        command = [self.baidupcs_path] + args

        logger.debug(f"Running command: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=300  # 5分钟超时
            )

            logger.debug(f"Command output: {result.stdout}")
            if result.stderr:
                logger.warning(f"Command stderr: {result.stderr}")

            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(command)}")
            raise Exception(f"Command timeout: {command}")
        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise

    def _run_command_chain(self, commands: List[List[str]]) -> Dict[str, any]:
        """
        在同一个BaiduPCS-Go进程中运行多个命令

        Args:
            commands: 命令列表，每个元素是一个命令参数列表

        Returns:
            包含stdout, stderr, returncode的字典
        """
        logger.debug(f"Running command chain with {len(commands)} commands")

        try:
            # 构建完整的命令序列
            command_sequence = []
            for cmd_args in commands:
                # 转换为BaiduPCS-Go命令格式
                cmd_str = ' '.join(cmd_args)
                command_sequence.append(cmd_str)

            # 使用换行符连接所有命令
            full_command = '\n'.join(command_sequence)

            logger.debug(f"Full command sequence:\n{full_command}")

            # 通过stdin传递给BaiduPCS-Go
            result = subprocess.run(
                [self.baidupcs_path],
                input=full_command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=300  # 5分钟超时
            )

            logger.debug(f"Command chain output: {result.stdout}")
            if result.stderr:
                logger.warning(f"Command chain stderr: {result.stderr}")

            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Command chain timeout")
            raise Exception(f"Command chain timeout")
        except Exception as e:
            logger.error(f"Command chain failed: {e}")
            raise

    def login(self) -> bool:
        """
        使用cookies登录百度账号

        Returns:
            登录是否成功
        """
        try:
            if not Path(self.cookies_path).exists():
                logger.error(f"Cookies file not found: {self.cookies_path}")
                return False

            # 读取 cookies 文件内容
            with open(self.cookies_path, 'r', encoding='utf-8') as f:
                cookies_content = f.read().strip()

            if not cookies_content:
                logger.error("Cookies file is empty")
                return False

            logger.info(f"Attempting to login with cookies from: {self.cookies_path}")

            result = self._run_command([
                'login',
                f'-cookies={cookies_content}'
            ])

            if result['returncode'] == 0:
                logger.info("Login successful")
                return True
            else:
                logger.error(f"Login failed: {result['stderr']}")
                logger.error(f"Login stdout: {result['stdout']}")
                return False

        except Exception as e:
            logger.error(f"Login exception: {e}")
            return False

    def detect_and_transfer_folder(self, share_link: str, code: str, target_folder: str) -> bool:
        """
        智能检测并转存文件夹：先临时转存检测内容，再决定是否保留

        策略：
        1. 使用临时文件夹名转存分享链接
        2. 检查转存后的内容是否包含PDF文件
        3. 如果包含PDF，重命名为目标文件夹名并返回成功
        4. 如果不包含PDF，清理临时内容并返回失败

        Args:
            share_link: 分享链接
            code: 提取码
            target_folder: 目标文件夹名

        Returns:
            是否成功转存包含PDF的文件夹
        """
        try:
            import uuid

            # 检查是否启用文件夹检测
            if not self.settings.enable_folder_detection:
                logger.info("Folder detection disabled, using direct transfer")
                return self.save_share_link(share_link, code, target_folder)

            logger.info(f"🔍 Starting smart folder detection for link ending with ...{share_link[-10:]}")
            logger.info(f"🎯 Target folder: {target_folder}")

            # 生成临时文件夹名
            temp_folder = f"{self.settings.temp_folder_prefix}{uuid.uuid4().hex[:8]}"

            logger.info(f"Step 1: Transferring to temporary folder: {temp_folder}")

            # 步骤1: 转存到临时文件夹
            if not self._transfer_to_temp(share_link, code, temp_folder):
                logger.warning("Transfer to temporary folder failed")
                return False

            logger.info(f"Step 2: Detecting content in temporary folder: {temp_folder}")

            # 步骤2: 检测临时文件夹内容
            detection_result = self._detect_folder_content(temp_folder)

            if detection_result['has_pdf']:
                pdf_count = detection_result['pdf_count']
                logger.info(f"Step 3: PDF files detected ({pdf_count} files), this is a valid folder")

                # 步骤3a: 包含PDF，重命名为目标文件夹名
                logger.info(f"Step 4: Renaming temporary folder to target: {temp_folder} -> {target_folder}")
                rename_result = self._run_command(['mv', f'//{temp_folder}', f'//{target_folder}'])

                if rename_result['returncode'] == 0:
                    logger.info(f"Successfully renamed to target folder: {target_folder}")
                    return True
                else:
                    logger.error(f"Failed to rename folder: {rename_result['stderr']}")
                    # 清理临时文件夹
                    self.delete_directory(temp_folder)
                    return False
            else:
                logger.info(f"Step 3: No PDF files detected, cleaning up temporary folder")
                # 步骤3b: 不包含PDF，清理临时文件夹
                self.delete_directory(temp_folder)
                logger.info("Temporary folder cleaned up, skipping this share link")
                return False

        except Exception as e:
            logger.error(f"Exception in smart folder detection: {e}")
            # 清理可能的临时文件
            try:
                self.delete_directory(temp_folder)
            except:
                pass
            return False

    def _transfer_to_temp(self, share_link: str, code: str, temp_folder: str) -> bool:
        """转存分享链接到临时文件夹"""
        try:
            # 切换到根目录
            self._run_command(['cd', '/'])

            # 去掉分享链接中的(pwd=xxx)部分，如果有的话
            clean_link = share_link.split('?pwd=')[0]

            # 使用 transfer 命令转存分享链接
            if code and code.strip():
                command = ['transfer', clean_link, code]
            else:
                command = ['transfer', clean_link]

            result = self._run_command(command)

            if result['returncode'] != 0:
                logger.error(f"Transfer command failed: {result['stderr']}")
                return False

            # 检查临时文件夹是否创建成功
            check_result = self._run_command(['ls', '/'])
            if check_result['returncode'] == 0:
                for line in check_result['stdout'].split('\n'):
                    if temp_folder in line and '/' in line:
                        logger.info(f"Temporary folder {temp_folder} created successfully")
                        return True

            logger.warning(f"Transfer command succeeded but temporary folder {temp_folder} not found")
            return False

        except Exception as e:
            logger.error(f"Exception in transfer to temp: {e}")
            return False

    def _detect_folder_content(self, folder_name: str) -> Dict[str, any]:
        """检测文件夹内容，判断是否包含PDF文件"""
        try:
            result = self._run_command(['ls', f'//{folder_name}'])

            if result['returncode'] != 0:
                logger.error(f"Failed to list folder content: {result['stderr']}")
                return {'has_pdf': False, 'pdf_count': 0}

            pdf_count = 0
            total_files = 0

            for line in result['stdout'].split('\n'):
                line = line.strip()
                if not line or line.startswith('#') or '----' in line or '当前目录' in line:
                    continue

                # 使用与list_pdf_files相同的解析逻辑
                match = re.match(r'^(\d+)\s+([\d.]+\s*[KBMG]+)\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(.+)$', line)
                if match:
                    parts = list(match.groups())
                    file_name = parts[4].strip()

                    # 检查是否为文件（不是目录）
                    if not file_name.endswith('/'):
                        total_files += 1
                        # 检查是否为PDF文件
                        if file_name.lower().endswith('.pdf'):
                            pdf_count += 1
                            logger.debug(f"Found PDF file: {file_name}")
                        else:
                            logger.debug(f"Found non-PDF file: {file_name}")

            logger.info(f"Folder content detection: {total_files} total files, {pdf_count} PDF files")

            return {
                'has_pdf': pdf_count > 0,
                'pdf_count': pdf_count,
                'total_files': total_files
            }

        except Exception as e:
            logger.error(f"Exception in folder content detection: {e}")
            return {'has_pdf': False, 'pdf_count': 0}

    def save_share_link(self, share_link: str, code: str, folder_name: str) -> bool:
        """
        转存分享链接到网盘目录

        Args:
            share_link: 分享链接
            code: 提取码
            folder_name: 目标目录名

        Returns:
            是否转存成功
        """
        try:
            # 切换到根目录
            self._run_command(['cd', '/'])

            # 检查目标目录是否已存在
            check_result = self._run_command(['ls', '/'])
            dir_exists = False
            if check_result['returncode'] == 0:
                for line in check_result['stdout'].split('\n'):
                    if folder_name in line and '/' in line:
                        dir_exists = True
                        break

            # 如果目录已存在，先删除再转存（避免重复内容）
            if dir_exists:
                logger.info(f"Target directory /{folder_name} already exists, deleting before transfer")
                self.delete_directory(folder_name)

            # 获取转存前的目录列表
            before_result = self._run_command(['ls', '/'])
            if before_result['returncode'] != 0:
                logger.error(f"Failed to list directory before transfer: {before_result['stderr']}")
                return False

            # 去掉分享链接中的(pwd=xxx)部分，如果有的话
            clean_link = share_link.split('?pwd=')[0]

            # 使用 transfer 命令转存分享链接
            if code and code.strip():
                command = ['transfer', clean_link, code]
            else:
                # 如果没有提取码，只传分享链接
                command = ['transfer', clean_link]

            result = self._run_command(command)

            if result['returncode'] != 0:
                logger.error(f"Save share link failed: {result['stderr']}")
                return False

            # 获取转存后的目录列表
            after_result = self._run_command(['ls', '/'])
            if after_result['returncode'] != 0:
                logger.error(f"Failed to list directory after transfer: {after_result['stderr']}")
                return False

            # 检查转存是否成功：查找目标目录是否存在
            transfer_success = False
            if folder_name:
                # 检查指定的目标目录是否存在
                for line in after_result['stdout'].split('\n'):
                    if folder_name in line and '/' in line and not line.strip().startswith('#') and '----' not in line:
                        transfer_success = True
                        logger.info(f"Share link saved to /{folder_name} (target directory exists)")
                        break

                # 如果目标目录不存在，尝试查找新转存的目录
                if not transfer_success:
                    new_items = self._find_new_items(before_result['stdout'], after_result['stdout'])
                    if new_items:
                        # 重命名新转存的目录为目标目录名
                        logger.info(f"Renaming transferred item from {new_items[0]} to {folder_name}")
                        rename_result = self._run_command(['mv', f'//{new_items[0]}', f'//{folder_name}'])
                        if rename_result['returncode'] == 0:
                            logger.info(f"Successfully renamed to /{folder_name}")
                            transfer_success = True
                        else:
                            logger.warning(f"Rename failed: {rename_result['stderr']}")
                    else:
                        logger.warning("No new items found after transfer, but command succeeded")
                        # 即使找不到新项目，如果转存命令成功，也认为转存成功
                        transfer_success = True
            else:
                # 没有指定目录名，查找新转存的目录
                new_items = self._find_new_items(before_result['stdout'], after_result['stdout'])
                if new_items:
                    logger.info(f"Share link saved to /{new_items[0]}")
                    transfer_success = True
                else:
                    logger.warning("No new items found after transfer, but command succeeded")
                    transfer_success = True

            return transfer_success

        except Exception as e:
            logger.error(f"Save share link exception: {e}")
            return False

    def _find_new_items(self, before_output: str, after_output: str) -> List[str]:
        """
        比较转存前后的目录列表，找出新增的项

        Args:
            before_output: 转存前的 ls 输出
            after_output: 转存后的 ls 输出

        Returns:
            新增的目录/文件名列表
        """
        before_items = set()
        after_items = set()

        # 解析转存前的目录列表
        for line in before_output.split('\n'):
            if '/' in line and not line.strip().startswith('#') and '----' not in line:
                parts = line.split()
                if parts:
                    item_name = parts[-1].rstrip('/')
                    if item_name and item_name not in ['.', '..']:
                        before_items.add(item_name)

        # 解析转存后的目录列表
        for line in after_output.split('\n'):
            if '/' in line and not line.strip().startswith('#') and '----' not in line:
                parts = line.split()
                if parts:
                    item_name = parts[-1].rstrip('/')
                    if item_name and item_name not in ['.', '..']:
                        after_items.add(item_name)

        # 找出新增的项
        new_items = after_items - before_items
        return list(new_items) if new_items else []

    def transfer_to_temp_and_get_folders(self, share_link: str, code: str) -> list:
        """
        转存分享链接到临时目录并获取所有转存的目录列表

        新的流程：
        1. 创建/清理 /temp_report 目录
        2. cd /temp_report
        3. transfer 分享链接
        4. ls 获取所有目录
        5. 返回目录列表（不删除/temp_report，便于后续下载）

        Args:
            share_link: 百度网盘分享链接
            code: 提取码

        Returns:
            目录名列表，如果失败则返回空列表
        """
        import time

        try:
            logger.info("=" * 60)
            logger.info("🔍 TRANSFER TO TEMP_REPORT AND GET FOLDERS")
            logger.info(f"📋 Share Link: {share_link[:80]}...")
            logger.info(f"🔑 Extraction Code: {code if code else 'None'}")

            # 使用固定临时目录名
            temp_dir_name = "temp_report"
            logger.info(f"📂 Step 1: Setting up temporary directory: /{temp_dir_name}")

            # 切换到根目录
            self._run_command(['cd', '/'])

            # 如果临时目录存在，先删除
            check_result = self._run_command(['ls', temp_dir_name])
            if check_result['returncode'] == 0:
                logger.info(f"🗑️  Removing existing temporary directory: /{temp_dir_name}")
                self.delete_directory(temp_dir_name)

            # 创建临时目录
            mkdir_result = self._run_command(['mkdir', temp_dir_name])
            if mkdir_result['returncode'] != 0:
                logger.error(f"❌ Failed to create temporary directory: {mkdir_result['stderr']}")
                return []
            logger.info(f"✅ Temporary directory created: /{temp_dir_name}")

            # 🔥 使用命令链在同一个BaiduPCS-Go会话中执行完整流程
            # delete, create, cd, transfer, ls（用户确认的正确流程）
            logger.info(f"📂 Step 2-3: Execute command chain in single BaiduPCS-Go session")

            # 去掉分享链接中的(pwd=xxx)部分，如果有的话
            clean_link = share_link.split('?pwd=')[0]
            logger.info(f"🔗 Cleaned link: {clean_link[:80]}...")

            # 🔥 构建完整的命令链：delete, create, cd, transfer, ls
            command_chain = []

            # 1. 切换到根目录
            command_chain.append(['cd', '/'])

            # 2. 🔥 关键修复：无条件删除/temp_report，无论是否存在
            # 这样确保不会因重复文件夹导致transfer失败
            command_chain.append(['rm', f'/{temp_dir_name}'])

            # 3. 创建临时目录
            command_chain.append(['mkdir', temp_dir_name])

            # 4. 切换到临时目录
            command_chain.append(['cd', f'/{temp_dir_name}'])

            # 5. 执行transfer命令
            if code and code.strip():
                command_chain.append(['transfer', clean_link, code])
            else:
                command_chain.append(['transfer', clean_link])

            # 6. 列出当前目录内容
            command_chain.append(['ls'])

            logger.info(f"🔧 Executing {len(command_chain)} commands in single session...")
            logger.info(f"📋 Command chain: cd / -> rm /{temp_dir_name} -> mkdir {temp_dir_name} -> cd /{temp_dir_name} -> transfer -> ls")

            # 在同一个BaiduPCS-Go进程中执行所有命令
            result = self._run_command_chain(command_chain)

            logger.info(f"📊 Command chain return code: {result['returncode']}")
            if result['stdout']:
                logger.info(f"📂 Command chain output:\n{result['stdout']}")
            if result['stderr']:
                logger.info(f"📂 Command chain stderr:\n{result['stderr']}")

            if result['returncode'] != 0:
                logger.error(f"❌ Command chain failed: {result['stderr']}")
                logger.error("❌ Possible reasons:")
                logger.error("   - Invalid share link")
                logger.error("   - Wrong extraction code")
                logger.error("   - Share link has expired")
                logger.error("   - Network connection issues")
                # 清理临时目录
                self.delete_directory(temp_dir_name)
                logger.info("=" * 60)
                return []

            logger.info("✅ Command chain completed successfully")

            # 🔥 从命令链输出中提取ls部分
            # ls输出通常在stdout的最后部分
            full_output = result['stdout']
            logger.info("📂 Step 4: Extracting ls output from command chain results...")

            # 查找ls命令的输出（通常是最后一部分）
            lines = full_output.split('\n')
            ls_output_lines = []

            # 从后往前找，找到ls输出的开始
            found_ls_start = False
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i].strip()

                # 如果找到了目录列表的特征行（包含日期时间和文件名），开始收集
                if not found_ls_start:
                    # 检查是否是目录列表的格式：日期时间 + 文件名
                    if re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', line):
                        found_ls_start = True
                        ls_output_lines.insert(0, line)
                else:
                    # 继续收集ls输出的行，直到遇到空行或新的命令提示
                    ls_output_lines.insert(0, line)
                    if line.startswith('#') or '----' in line or '当前目录' in line:
                        continue
                    # 如果遇到看起来像命令输出的行，停止收集
                    if line and not line.startswith('#') and '----' not in line and '当前目录' not in line:
                        if not re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', line):
                            break

            ls_output = '\n'.join(ls_output_lines)

            if not ls_output or not found_ls_start:
                logger.warning("⚠️  Could not extract ls output from command chain")
                logger.warning("⚠️  Using full output for parsing")
                ls_output = full_output
            else:
                logger.info(f"✅ Extracted ls output from command chain:")
                logger.info(f"📂 Extracted ls output:\n{ls_output}")

            # 从目录列表中解析所有文件夹名
            folders = self._extract_all_folders_from_ls_output(ls_output)

            if not folders:
                logger.error("❌ No folders found in /temp_report")
                logger.error("❌ Transfer may have failed or created unexpected structure")
                # 保留/temp_report用于调试
                logger.info("📂 /temp_report preserved for debugging")
                logger.info("=" * 60)
                return []

            logger.info(f"🎯 SUCCESS - Found {len(folders)} folder(s): {folders}")
            logger.info("📂 /temp_report preserved - ready for download processing")
            logger.info("=" * 60)
            logger.info(f"🏁 FOLDERS READY FOR PROCESSING: {folders}")
            logger.info("=" * 60)

            return folders

        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"❌ EXCEPTION IN transfer_to_temp_and_get_folders: {e}")
            logger.error("❌ This could be caused by:")
            logger.error("   - BaiduPCS-Go execution errors")
            logger.error("   - Command parsing failures")
            logger.error("   - Unexpected output format")
            logger.error("   - File system issues")
            logger.info("=" * 60)
            return []

    def get_real_folder_name_from_share(self, share_link: str, code: str) -> Optional[str]:
        """
        从分享链接获取真实的文件夹名称

        通过创建临时目录并转存到该目录，然后列出内容来获取真实文件夹名称。

        策略：
        1. 创建唯一临时目录（如 /temp_folder_abcd）
        2. 如果目录存在则删除
        3. cd 到临时目录
        4. transfer url code 到当前目录
        5. 列出当前目录内容，获取真实文件夹名
        6. 删除临时目录

        Args:
            share_link: 百度网盘分享链接
            code: 提取码

        Returns:
            真实的文件夹名称，如果获取失败则返回None
        """
        import time

        try:
            logger.info("=" * 60)
            logger.info("🔍 BAIDUPCS-GO FOLDER NAME DETECTION STARTED")
            logger.info(f"📋 Share Link: {share_link[:80]}...")
            logger.info(f"🔑 Extraction Code: {code if code else 'None'}")

            # 使用固定临时目录名
            temp_dir_name = "temp_report"
            logger.info(f"📂 Step 1: Creating temporary directory: /{temp_dir_name}")

            # 切换到根目录
            self._run_command(['cd', '/'])

            # 如果临时目录存在，先删除
            check_result = self._run_command(['ls', temp_dir_name])
            if check_result['returncode'] == 0:
                logger.info(f"🗑️  Removing existing temporary directory: /{temp_dir_name}")
                self.delete_directory(temp_dir_name)

            # 创建临时目录
            mkdir_result = self._run_command(['mkdir', temp_dir_name])
            if mkdir_result['returncode'] != 0:
                logger.error(f"❌ Failed to create temporary directory: {mkdir_result['stderr']}")
                return None
            logger.info(f"✅ Temporary directory created: /{temp_dir_name}")

            # 切换到临时目录
            logger.info(f"📂 Step 2: Switching to temporary directory: /{temp_dir_name}")
            cd_result = self._run_command(['cd', f'/{temp_dir_name}'])
            if cd_result['returncode'] != 0:
                logger.error(f"❌ Failed to switch to temporary directory: {cd_result['stderr']}")
                self.delete_directory(temp_dir_name)
                return None
            logger.info(f"✅ Now in temporary directory: /{temp_dir_name}")

            # 转存分享链接到当前目录
            logger.info("📂 Step 3: Transferring share link to temporary directory...")

            # 去掉分享链接中的(pwd=xxx)部分，如果有的话
            clean_link = share_link.split('?pwd=')[0]
            logger.info(f"🔗 Cleaned link: {clean_link[:80]}...")

            if code and code.strip():
                command = ['transfer', clean_link, code]
                logger.info(f"🔧 Command: transfer {clean_link[:50]}... {code}")
            else:
                command = ['transfer', clean_link]
                logger.info(f"🔧 Command: transfer {clean_link[:50]}... (no code)")

            result = self._run_command(command)

            logger.info(f"📊 Transfer command return code: {result['returncode']}")
            if result['stdout']:
                logger.info(f"📂 Transfer stdout:\n{result['stdout']}")
            if result['stderr']:
                logger.info(f"📂 Transfer stderr:\n{result['stderr']}")

            if result['returncode'] != 0:
                logger.error(f"❌ Transfer failed: {result['stderr']}")
                logger.error("❌ Possible reasons:")
                logger.error("   - Invalid share link")
                logger.error("   - Wrong extraction code")
                logger.error("   - Share link has expired")
                logger.error("   - Network connection issues")
                # 清理临时目录
                self.delete_directory(temp_dir_name)
                logger.info("=" * 60)
                return None

            logger.info("✅ Transfer command completed successfully")

            # 列出当前目录内容，获取真实文件夹名
            logger.info("📂 Step 4: Listing current directory contents...")
            time.sleep(1)  # 等待一秒确保文件系统更新

            ls_result = self._run_command(['ls'])
            if ls_result['returncode'] != 0:
                logger.error(f"❌ Failed to list directory: {ls_result['stderr']}")
                self.delete_directory(temp_dir_name)
                return None

            logger.info(f"📂 Current directory contents:\n{ls_result['stdout']}")

            # 从目录列表中解析文件夹名
            real_folder_name = self._extract_folder_name_from_ls_output(ls_result['stdout'])

            if not real_folder_name:
                logger.error("❌ Could not extract folder name from directory listing")
                logger.error("❌ No subdirectories found in temporary directory")
                # 清理临时目录
                self.delete_directory(temp_dir_name)
                logger.info("=" * 60)
                return None

            if not real_folder_name:
                logger.error("❌ Could not extract folder name from directory listing")
                logger.error("❌ No subdirectories found in temporary directory")
                logger.error("❌ /temp_report directory preserved for debugging")
                logger.info("=" * 60)
                return None

            logger.info(f"🎯 SUCCESS - Found real folder name: {real_folder_name}")

            # 🔥 重要：不删除临时目录，保留用于调试
            logger.info("📂 Step 5: Preserving /temp_report directory for debugging...")
            logger.info("🔍 You can manually check: BaiduPCS-Go ls /temp_report")
            logger.info("🗑️  To clean up manually: BaiduPCS-Go rm /temp_report")

            logger.info("=" * 60)
            logger.info(f"🏁 FOLDER NAME DETECTION COMPLETED: {real_folder_name}")
            logger.info("📂 /temp_report preserved - please check transfer results manually")
            logger.info("=" * 60)

            return real_folder_name

        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"❌ EXCEPTION IN get_real_folder_name_from_share: {e}")
            logger.error("❌ This could be caused by:")
            logger.error("   - BaiduPCS-Go execution errors")
            logger.error("   - Command parsing failures")
            logger.error("   - Unexpected output format")
            logger.error("   - File system issues")
            logger.info("=" * 60)
            return None

    def _extract_folder_name_from_transfer_output(self, output: str) -> Optional[str]:
        """
        从 BaiduPCS-Go transfer 输出中解析文件夹名称

        BaiduPCS-Go 的 transfer 输出通常包含类似这样的信息：
        - "已转存 /我的文档"
        - "转存成功: /目标文件夹"
        - "已保存到 /文件夹名"

        Args:
            output: transfer 命令的输出（stdout 或 stderr）

        Returns:
            解析出的文件夹名称，如果解析失败则返回 None
        """
        if not output:
            return None

        logger.debug(f"🔍 Parsing transfer output for folder name...")
        logger.debug(f"📂 Output content: {output[:200]}...")

        # 常见的 BaiduPCS-Go 输出模式（按优先级排序）
        patterns = [
            r'保存了\s*([^\s，,\r\n]+)\s*到',                           # 保存了260816到（最常见格式）
            r'分享链接转存到网盘成功[,，]\s*保存了([^\s，,\r\n]+)\s*到',  # 分享链接转存到网盘成功,保存了260816到
            r'已转存\s+([/\s\S]*?)[\s\r\n]',                           # 已转存 /文件夹名
            r'转存成功[:：]\s*([/\s\S]*?)[\s\r\n]',                    # 转存成功: /文件夹名
            r'已保存到\s+([/\s\S]*?)[\s\r\n]',                         # 已保存到 /文件夹名
            r'保存到\s+([/\s\S]*?)[\s\r\n]',                           # 保存到 /文件夹名
            r'[/\\]([^/\s\r\n]+)[\s\r\n]*$',                           # /文件夹名（在行尾）
        ]

        import re
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                folder_name = match.group(1).strip()
                # 移除可能的路径前缀
                folder_name = folder_name.rstrip('/').rstrip('\\')
                # 提取最后的部分作为文件夹名
                if '/' in folder_name:
                    folder_name = folder_name.split('/')[-1]
                if '\\' in folder_name:
                    folder_name = folder_name.split('\\')[-1]

                if folder_name and len(folder_name) > 0:
                    logger.info(f"✅ Folder name extracted using pattern: {pattern[:20]}...")
                    logger.info(f"📂 Extracted folder: {folder_name}")
                    return folder_name

        logger.warning("⚠️  Could not extract folder name from transfer output")
        logger.debug("⚠️  Tried patterns but none matched")
        return None

    def _extract_folder_name_from_duplicate_message(self, output: str) -> Optional[str]:
        """
        从"文件重复"错误消息中提取文件夹名

        Args:
            output: 错误消息输出

        Returns:
            文件夹名，如果提取失败则返回 None
        """
        if not output:
            return None

        logger.debug(f"🔍 Searching for folder name in duplicate message...")

        # 尝试从错误消息中提取可能的文件夹名
        # BaiduPCS-Go 可能在错误消息中提到具体的文件夹名
        import re

        # 查找可能的文件夹名模式（通常是数字格式，如 260817）
        patterns = [
            r'/(\d{6,7})',           # /260817 格式
            r'重复[:：]\s*/?(\w+)',  # 重复:/260817 格式
            r'目录[:：]\s*(\w+)',     # 目录:260817 格式
        ]

        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                folder_name = match.group(1)
                logger.info(f"📂 Potential folder name found in error: {folder_name}")
                return folder_name

        logger.debug("🔍 No folder name found in duplicate message")
        return None

    def _find_matching_folder_from_existing(self, existing_output: str) -> Optional[str]:
        """
        从现有目录列表中查找可能的匹配文件夹

        基于时间戳和模式匹配查找最近创建的相关文件夹

        Args:
            existing_output: 现有目录列表输出

        Returns:
            匹配的文件夹名，如果未找到则返回 None
        """
        if not existing_output:
            return None

        logger.debug(f"🔍 Searching for matching folder in existing directories...")

        import re
        from datetime import datetime, timedelta

        # 解析现有目录，寻找最近创建的数字格式文件夹
        lines = existing_output.split('\n')
        candidates = []

        for line in lines:
            # 匹配数字格式的文件夹名（如 260816, 260817）
            match = re.search(r'/(\d{6,7})/\s*', line)
            if match:
                folder_name = match.group(1)

                # 尝试解析日期时间信息
                time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
                if time_match:
                    try:
                        folder_time = datetime.strptime(time_match.group(1), '%Y-%m-%d %H:%M:%S')
                        candidates.append((folder_name, folder_time))
                    except ValueError:
                        continue

        # 按时间排序，返回最新的文件夹
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            latest_folder = candidates[0][0]
            logger.info(f"📂 Found latest matching folder: {latest_folder}")
            return latest_folder

        logger.debug("🔍 No matching folder found in existing directories")
        return None

    def _extract_folder_name_from_ls_output(self, ls_output: str) -> Optional[str]:
        """
        从 ls 输出中解析文件夹名称

        Args:
            ls_output: ls 命令的输出

        Returns:
            文件夹名称，如果解析失败则返回 None
        """
        if not ls_output:
            logger.error("❌ ls_output is empty")
            return None

        logger.info("=" * 60)
        logger.info("🔍 PARSING FOLDER NAME FROM LS OUTPUT")
        logger.info("=" * 60)
        logger.info(f"📂 Raw ls output:\n{ls_output}")
        logger.info("=" * 60)

        import re
        lines = ls_output.split('\n')
        folders = []
        all_items = []

        logger.info(f"📋 Processing {len(lines)} lines...")

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # 跳过标题行和分隔线
            if not line_stripped or line_stripped.startswith('#') or '----' in line_stripped or '当前目录' in line_stripped:
                logger.debug(f"Line {line_num}: SKIP (header/empty)")
                continue

            logger.debug(f"Line {line_num}: {line_stripped[:80]}...")

            # 🔥 增强检测：支持多种目录格式
            # 格式1: 结尾带 / 的目录
            if line_stripped.endswith('/'):
                folder_name = line_stripped.rstrip('/')
                # 提取最后一部分作为文件夹名
                if '/' in folder_name:
                    folder_name = folder_name.split('/')[-1]

                if folder_name and folder_name not in ['.', '..']:
                    folders.append(folder_name)
                    logger.info(f"✅ Line {line_num}: Found folder (format /): {folder_name}")
                    continue

            # 格式2: (dir) 标记
            if '(dir)' in line_stripped:
                # 提取文件名列（通常在最后一列，(dir)前）
                parts = line_stripped.split()
                if len(parts) >= 2:
                    # 取倒数第二个元素（倒数第一个是(dir)）
                    folder_name = parts[-2].strip()
                    if folder_name and folder_name not in ['.', '..']:
                        folders.append(folder_name)
                        logger.info(f"✅ Line {line_num}: Found folder (format dir): {folder_name}")
                        continue

            # 格式3: 数字格式的文件夹名（如 260817）
            match = re.search(r'\s(\d{6,7})\s', line_stripped)
            if match:
                folder_name = match.group(1)
                folders.append(folder_name)
                logger.info(f"✅ Line {line_num}: Found folder (format number): {folder_name}")
                continue

            # 记录所有非空行用于调试
            all_items.append(line_stripped)

        logger.info("=" * 60)
        logger.info(f"📊 PARSING SUMMARY:")
        logger.info(f"📋 Total lines: {len(lines)}")
        logger.info(f"📂 Folders found: {len(folders)}")
        logger.info(f"📂 Folder names: {folders}")
        logger.info(f"📋 All non-header items: {all_items[:5]}...")  # 显示前5个
        logger.info("=" * 60)

        if not folders:
            logger.error("❌ NO FOLDERS FOUND IN LS OUTPUT")
            logger.error("❌ This might indicate:")
            logger.error("   1. Transfer didn't create expected subdirectory")
            logger.error("   2. Files are directly in /temp_report (not in a subfolder)")
            logger.error("   3. Output format doesn't match expected patterns")
            logger.error(f"❌ First few items for manual inspection: {all_items[:3]}")
            return None

        # 如果有多个文件夹，选择第一个（通常是最新转存的）
        if len(folders) > 1:
            logger.info(f"📂 Found {len(folders)} folders, using the first one: {folders[0]}")
            logger.info(f"📂 All folder options: {folders}")
        else:
            logger.info(f"📂 Found folder: {folders[0]}")

        return folders[0]

    def _extract_all_folders_from_ls_output(self, ls_output: str) -> list:
        """
        从 ls 输出中解析所有文件夹名称

        基于用户提供的实际格式：
        10           -  2026-08-08 22:52:10  260726/
        11           -  2026-08-08 22:52:29  260727/

        Args:
            ls_output: ls 命令的输出

        Returns:
            所有文件夹名称的列表
        """
        if not ls_output:
            logger.error("❌ ls_output is empty")
            return []

        logger.info("=" * 60)
        logger.info("🔍 EXTRACTING ALL FOLDERS FROM LS OUTPUT")
        logger.info("=" * 60)
        logger.info(f"📂 Raw ls output:\n{ls_output}")
        logger.info("=" * 60)

        import re
        lines = ls_output.split('\n')
        folders = []

        logger.info(f"📋 Processing {len(lines)} lines...")

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # 跳过空行和标题行
            if not line_stripped or line_stripped.startswith('#') or '----' in line_stripped or '当前目录' in line_stripped:
                continue

            # 🔥 基于用户实际格式的解析：查找以 / 结尾的文件夹
            # 格式：序号  -  日期时间  文件夹名/
            if '/' in line_stripped and line_stripped.endswith('/'):
                # 提取文件夹名（去掉末尾的/）
                parts = line_stripped.split()
                for part in reversed(parts):
                    if part.endswith('/'):
                        folder_name = part.rstrip('/')
                        # 验证是数字格式的文件夹（如260726）
                        if folder_name.isdigit() and len(folder_name) == 6:
                            folders.append(folder_name)
                            logger.info(f"✅ Line {line_num}: Found folder: {folder_name}")
                            break

        logger.info("=" * 60)
        logger.info(f"📊 EXTRACTION SUMMARY:")
        logger.info(f"📋 Total lines: {len(lines)}")
        logger.info(f"📂 Folders found: {len(folders)}")
        logger.info(f"📂 Folder names: {folders}")
        logger.info("=" * 60)

        return folders

    def delete_directory(self, folder_name: str) -> bool:
        """
        删除网盘目录

        Args:
            folder_name: 目录名

        Returns:
            是否删除成功
        """
        try:
            result = self._run_command([
                'rm',
                f'//{folder_name}'
            ])

            if result['returncode'] == 0:
                logger.info(f"Directory /{folder_name} deleted")
                return True
            else:
                logger.warning(f"Delete directory failed: {result['stderr']}")
                return False

        except Exception as e:
            logger.error(f"Delete directory exception: {e}")
            return False

    def list_pdf_files(self, folder_name: str) -> List[Dict[str, any]]:
        """
        列出目录中的PDF文件

        Args:
            folder_name: 目录名

        Returns:
            PDF文件列表，每个元素包含name和size
        """
        try:
            result = self._run_command([
                'ls',
                f'//{folder_name}'
            ])

            if result['returncode'] != 0:
                logger.error(f"List files failed: {result['stderr']}")
                return []

            # 解析输出，找出PDF文件
            pdf_files = []
            for line in result['stdout'].split('\n'):
                line = line.strip()
                if not line or line.startswith('#') or '----' in line or '当前目录' in line:
                    continue

                logger.debug(f"Processing line: {line[:100]}...")  # 调试信息

                # BaiduPCS-Go输出格式：
                # 序号    大小         日期    时间               文件名
                # 0       7.00MB      2026-07-12 09:12:43  Long filename with spaces.pdf
                # 使用正则表达式精确匹配前4个字段，保留文件名的原始空格
                match = re.match(r'^(\d+)\s+([\d.]+\s*[KBMG]+)\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(.+)$', line)
                if match:
                    # 提取字段
                    parts = list(match.groups())
                    # 前4个字段是：序号、大小、日期、时间
                    # 第5个字段是文件名（保留原始空格）
                    file_name = parts[4].strip()  # 文件名，去除首尾空格
                    file_size_str = parts[1]  # 大小在第2个位置

                    # 🔥 关键修复：确保文件名不为空
                    if not file_name:
                        logger.warning(f"Empty filename detected in line: {line[:100]}")
                        continue

                    # 只处理PDF文件
                    if file_name.lower().endswith('.pdf') and not file_name.endswith('/'):
                        # 🔥 构造完整路径，确保格式正确
                        full_path = f'//{folder_name}/{file_name}'

                        logger.debug(f"Found PDF file: {file_name[:50]}...")
                        logger.debug(f"Full path: {full_path[:80]}...")

                        # 解析文件大小
                        try:
                            if 'MB' in file_size_str:
                                size_mb = float(file_size_str.replace('MB', '').replace('mb', ''))
                                file_size = int(size_mb * 1024 * 1024)
                            elif 'KB' in file_size_str:
                                size_kb = float(file_size_str.replace('KB', '').replace('kb', ''))
                                file_size = int(size_kb * 1024)
                            elif 'GB' in file_size_str:
                                size_gb = float(file_size_str.replace('GB', '').replace('gb', ''))
                                file_size = int(size_gb * 1024 * 1024 * 1024)
                            else:
                                file_size = int(file_size_str) if file_size_str.isdigit() else 0
                        except:
                            file_size = 0

                        # 🔥 添加调试信息，确保路径不为空
                        if not full_path or full_path == f'//{folder_name}/':
                            logger.error(f"Invalid full_path generated: '{full_path}' from file_name: '{file_name}'")
                            continue

                        pdf_files.append({
                            'name': full_path,
                            'size': file_size
                        })

                        logger.debug(f"Added PDF file: {full_path[:60]}... ({file_size} bytes)")
                    else:
                        logger.debug(f"Skipping non-PDF file: {file_name[:50] if file_name else 'empty'}")

            logger.info(f"Found {len(pdf_files)} PDF files in //{folder_name}")
            return pdf_files

        except Exception as e:
            logger.error(f"List files exception: {e}")
            return []

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        下载文件到本地

        Args:
            remote_path: 远程文件路径
            local_path: 本地保存路径

        Returns:
            是否下载成功
        """
        try:
            # 确保本地目录存在
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)

            # 🔥 基于用户验证：超长文件名可以直接下载成功
            # 不再使用重命名workaround策略，简化下载逻辑
            # 所有文件统一使用正常下载流程

            # 🔥 关键修复：使用配置的temp_dir下的临时子目录，避免删除用户主目录
            # 创建唯一临时子目录，避免冲突
            temp_subdir = os.path.join(self.temp_dir, f"download_{uuid.uuid4().hex[:8]}")
            download_dir = temp_subdir

            # 🔥 确保临时子目录存在（关键修复！）
            os.makedirs(download_dir, exist_ok=True)

            # 使用配置的savedir，设置为download目录
            self._run_command(['config', 'set', '-savedir', download_dir])

            logger.debug(f"Downloading {remote_path} to {download_dir}")

            result = self._run_command([
                'download',
                remote_path
            ])

            # 🔥 增强验证：检查BaiduPCS-Go输出中的错误信息
            stdout_lower = result['stdout'].lower()
            stderr_lower = result['stderr'].lower()

            # 检查是否有错误关键词（即使returncode是0）
            error_keywords = ['error', 'failed', '失败', '错误', 'not found', '不存在']
            has_error_in_output = any(keyword in stdout_lower or keyword in stderr_lower for keyword in error_keywords)

            if result['returncode'] == 0 and not has_error_in_output:
                # BaiduPCS-Go 会将文件下载到配置的savedir
                # 文件名可能与原始名称不同（特别是中文或特殊字符）
                # 我们需要查找最新下载的文件

                downloaded_file = self._find_downloaded_file(download_dir, remote_path)
                if downloaded_file and os.path.exists(downloaded_file):
                    file_size = os.path.getsize(downloaded_file)
                    logger.info(f"File downloaded: {remote_path} -> {downloaded_file} ({file_size} bytes)")

                    # 🔥 关键验证：检查文件大小是否合理（大于0）
                    if file_size == 0:
                        logger.error(f"Downloaded file is empty (0 bytes): {downloaded_file}")
                        # 清理临时子目录
                        import shutil
                        shutil.rmtree(download_dir, ignore_errors=True)
                        return False

                    # 如果下载的文件路径与期望的路径不同，移动文件
                    if downloaded_file != local_path:
                        import shutil
                        try:
                            # 确保目标目录存在
                            target_dir = os.path.dirname(local_path)
                            if target_dir:
                                os.makedirs(target_dir, exist_ok=True)

                            # 对于超长路径，使用特殊处理
                            if len(downloaded_file) > 250:
                                logger.info(f"Path too long ({len(downloaded_file)} chars), using special handling")
                                # 尝试使用文件句柄直接复制（避免路径长度限制）
                                try:
                                    with open(downloaded_file, 'rb') as src_file:
                                        with open(local_path, 'wb') as dst_file:
                                            dst_file.write(src_file.read())
                                    logger.info(f"Copied file using file handles: {local_path}")
                                except Exception as file_error:
                                    logger.warning(f"File handle copy failed: {file_error}, trying shutil.copy2")
                                    shutil.copy2(downloaded_file, local_path)
                                    logger.info(f"Copied file using shutil.copy2: {local_path}")
                            else:
                                # 正常路径，直接移动
                                shutil.move(downloaded_file, local_path)
                                logger.info(f"Moved file from {downloaded_file} to {local_path}")

                        except Exception as e:
                            logger.error(f"Failed to move/copy file from {downloaded_file} to {local_path}: {e}")
                            # 如果移动失败，直接使用下载的文件路径
                            logger.warning(f"Using downloaded file path instead: {downloaded_file}")
                            local_path = downloaded_file  # 使用实际的下载路径

                    # 验证文件是否存在且不为空
                    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                        logger.info(f"File verified at: {local_path}")
                        # 🔥 清理临时下载目录
                        import shutil
                        shutil.rmtree(download_dir, ignore_errors=True)
                        return True
                    else:
                        logger.error(f"Downloaded file is empty or missing: {local_path}")
                        # 清理临时下载目录
                        import shutil
                        shutil.rmtree(download_dir, ignore_errors=True)
                        return False
                else:
                    logger.error(f"Download command succeeded but file not found in {download_dir}")
                    logger.info(f"Expected file at: {local_path}")
                    # 🔥 关键诊断：显示BaiduPCS-Go的实际输出，帮助定位问题
                    logger.info(f"BaiduPCS-Go stdout: {result['stdout'][:500]}")
                    logger.info(f"BaiduPCS-Go stderr: {result['stderr'][:500]}")
                    logger.info(f"Remote path length: {len(remote_path)} characters")
                    # 清理临时目录
                    import shutil
                    shutil.rmtree(download_dir, ignore_errors=True)
                    return False
            else:
                # 🔥 处理BaiduPCS-Go返回失败或有错误信息的情况
                error_reason = "returncode != 0" if result['returncode'] != 0 else "error keywords found in output"
                logger.error(f"Download command failed ({error_reason}): {result['stderr']}")
                logger.info(f"Download stdout: {result['stdout'][:500]}")
                logger.info(f"Remote path: {remote_path[:100]}... (length: {len(remote_path)})")
                # 清理临时目录
                import shutil
                shutil.rmtree(download_dir, ignore_errors=True)
                return False
        except Exception as e:
            logger.error(f"Download exception: {e}")
            # 清理临时下载目录
            import shutil
            if 'download_dir' in locals():
                shutil.rmtree(download_dir, ignore_errors=True)
            return False

    def _cleanup_download_dir(self, download_dir: str):
        """清理下载目录（包括子目录）"""
        try:
            if not os.path.exists(download_dir):
                return

            # 使用更可靠的方法删除目录内容
            import shutil
            try:
                # 直接删除整个目录然后重新创建
                shutil.rmtree(download_dir, ignore_errors=True)
                os.makedirs(download_dir, exist_ok=True)
                logger.debug(f"Cleaned up download directory: {download_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup with shutil, trying manual cleanup: {e}")

                # 备用方案：逐个文件删除
                try:
                    for root, dirs, files in os.walk(download_dir, topdown=False):
                        # 先删除文件
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                # 使用Windows短路径格式处理长文件名
                                if len(file_path) > 250:
                                    # Windows长路径处理
                                    import pathlib
                                    file_path = pathlib.Path(file_path)
                                os.remove(file_path)
                                logger.debug(f"Cleaned up existing file: {file}")
                            except Exception as file_error:
                                logger.debug(f"Failed to remove file {file}: {file_error}")

                        # 再删除空目录
                        for dir in dirs:
                            try:
                                dir_path = os.path.join(root, dir)
                                os.rmdir(dir_path)
                                logger.debug(f"Removed empty directory: {dir_path}")
                            except Exception as dir_error:
                                logger.debug(f"Failed to remove directory {dir}: {dir_error}")
                except Exception as walk_error:
                    logger.warning(f"Manual cleanup also failed: {walk_error}")

        except Exception as e:
            logger.warning(f"Failed to cleanup download directory: {e}")

    def _find_downloaded_file(self, download_dir: str, remote_path: str) -> str:
        """查找下载的文件（处理文件名修改和子目录的情况）"""
        try:
            if not os.path.exists(download_dir):
                logger.warning(f"Download directory does not exist: {download_dir}")
                return None

            # 🔥 关键修复：使用Windows长路径支持处理超长路径
            # 在Windows上，路径可能超过MAX_PATH (260字符)限制
            def handle_long_path(path):
                """处理Windows长路径问题"""
                if len(path) > 250:
                    # Windows长路径前缀：\\?\ 支持最长32,767字符
                    if not path.startswith('\\\\?\\'):
                        return '\\\\?\\' + os.path.abspath(path)
                return path

            # 递归搜索所有文件，处理超长路径
            all_files = []
            try:
                for root, dirs, files in os.walk(download_dir):
                    for file in files:
                        try:
                            # 尝试正常路径
                            file_path = os.path.join(root, file)
                            if os.path.exists(file_path):
                                all_files.append(file_path)
                            else:
                                # 尝试长路径格式
                                long_path = handle_long_path(file_path)
                                if os.path.exists(long_path):
                                    all_files.append(long_path)
                        except Exception as file_error:
                            logger.debug(f"Skipping file due to error: {file} - {file_error}")
            except Exception as walk_error:
                logger.warning(f"Failed to walk directory normally: {walk_error}")
                # 备用方案：使用glob模式搜索
                import glob
                try:
                    # 搜索所有PDF文件
                    pdf_pattern = os.path.join(download_dir, '**', '*.pdf')
                    for pdf_file in glob.glob(pdf_pattern, recursive=True):
                        try:
                            if os.path.exists(pdf_file):
                                all_files.append(pdf_file)
                        except:
                            pass
                except Exception as glob_error:
                    logger.error(f"Glob search also failed: {glob_error}")

            logger.info(f"File search: Looking in {download_dir}, found {len(all_files)} files total")

            if not all_files:
                logger.warning(f"No files found in download directory: {download_dir}")
                return None

            logger.debug(f"Found {len(all_files)} files in download directory")
            for file_path in all_files[:5]:  # 只显示前5个文件
                logger.debug(f"  - {file_path}")

            # 如果只有一个文件，很可能是下载的文件
            if len(all_files) == 1:
                return all_files[0]

            # 如果有多个文件，尝试找到最匹配的
            remote_basename = os.path.basename(remote_path)
            remote_basename_no_ext = os.path.splitext(remote_basename)[0]

            logger.info(f"Looking for file: {remote_basename}")
            logger.info(f"Looking for base name: {remote_basename_no_ext}")

            # 首先尝试精确匹配
            for file_path in all_files:
                try:
                    file_name = os.path.basename(file_path)
                    file_no_ext = os.path.splitext(file_name)[0]

                    if file_no_ext == remote_basename_no_ext:
                        logger.info(f"Found exact match: {file_path}")
                        return file_path
                except Exception as match_error:
                    logger.debug(f"Error matching file {file_path}: {match_error}")

            # 如果没有精确匹配，尝试更智能的部分匹配
            # 提取关键词进行匹配（厂商名、报告类型等）
            def extract_keywords(filename):
                """从文件名中提取关键词"""
                keywords = []
                # 常见投资银行关键词
                banks = ['Goldman Sachs', 'Morgan Stanley', 'J.P. Morgan', 'JPM', 'Nomura', 'UBS', 'Citi', 'Bank of America']
                for bank in banks:
                    if bank in filename:
                        keywords.append(bank)

                # 提取数字编号（如 260713）
                numbers = re.findall(r'\d{4,}', filename)
                if numbers:
                    keywords.extend(numbers)

                return keywords

            remote_keywords = extract_keywords(remote_basename_no_ext)
            logger.info(f"Remote file keywords: {remote_keywords}")

            # 根据关键词匹配
            for file_path in all_files:
                try:
                    file_name = os.path.basename(file_path)
                    file_no_ext = os.path.splitext(file_name)[0]

                    file_keywords = extract_keywords(file_no_ext)
                    logger.debug(f"Checking {file_no_ext}, keywords: {file_keywords}")

                    # 检查关键词匹配度
                    if remote_keywords and file_keywords:
                        match_count = sum(1 for kw in remote_keywords if kw in file_keywords)
                        if match_count >= len(remote_keywords):  # 所有关键词都匹配
                            logger.info(f"Found keyword match: {file_path}")
                            return file_path
                except Exception as keyword_error:
                    logger.debug(f"Error checking keywords for {file_path}: {keyword_error}")

            # 如果没有找到匹配的，返回最新的文件
            try:
                files_with_time = [(f, os.path.getmtime(f)) for f in all_files]
                files_with_time.sort(key=lambda x: x[1], reverse=True)
                latest_file = files_with_time[0][0]
                logger.debug(f"Using latest file: {latest_file}")
                return latest_file
            except Exception as time_error:
                logger.warning(f"Failed to get file times: {time_error}")
                return all_files[0]  # 返回第一个文件

        except Exception as e:
            logger.warning(f"Failed to find downloaded file: {e}")
            return None

    def _download_long_filename(self, remote_path: str, local_path: str) -> bool:
        """
        下载超长文件名的文件，使用重命名绕过策略

        策略：
        1. 在百度网盘中将超长文件重命名为临时短文件名
        2. 下载短文件名
        3. 在本地重命名回长文件名
        4. 在百度网盘中重命名回原文件名

        Args:
            remote_path: 远程文件路径（超长文件名）
            local_path: 本地保存路径

        Returns:
            是否下载成功
        """
        try:
            import uuid
            import shutil

            remote_dir = os.path.dirname(remote_path)
            original_filename = os.path.basename(remote_path)

            # 生成临时短文件名
            temp_short_name = f"temp_download_{uuid.uuid4().hex[:8]}.pdf"
            temp_remote_path = f"{remote_dir}/{temp_short_name}"

            logger.info(f"Using rename workaround for long filename")
            logger.info(f"Original: {original_filename[:80]}... ({len(original_filename)} chars)")
            logger.info(f"Temporary: {temp_short_name}")

            # 步骤1：在百度网盘中重命名文件
            logger.info(f"Step 1: Renaming in Baidu cloud...")
            rename_result = self._run_command([
                'rename',
                remote_path,
                temp_short_name
            ])

            if rename_result['returncode'] != 0:
                logger.error(f"Failed to rename in Baidu cloud: {rename_result['stderr']}")
                return False

            logger.info(f"Successfully renamed to {temp_short_name}")

            try:
                # 步骤2：下载短文件名（使用正常的下载流程）
                logger.info(f"Step 2: Downloading with short filename...")
                logger.info(f"🔍 DEBUG: temp_remote_path = {temp_remote_path}")
                logger.info(f"🔍 DEBUG: local_path = {local_path}")
                download_success = self._download_with_normal_flow(temp_remote_path, local_path)

                if download_success:
                    logger.info(f"Step 3: Successfully downloaded, verifying file...")
                    # 步骤3：验证文件是否正确下载
                    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                        file_size = os.path.getsize(local_path)
                        logger.info(f"✅ Long filename download successful: {file_size} bytes")
                        return True
                    else:
                        logger.error(f"Downloaded file not found or empty: {local_path}")
                        return False
                else:
                    logger.error(f"Download with short filename failed")
                    return False

            finally:
                # 步骤4：无论下载成功与否，都尝试在百度网盘中重命名回原文件名
                logger.info(f"Step 4: Restoring original filename in Baidu cloud...")
                try:
                    restore_result = self._run_command([
                        'rename',
                        temp_remote_path,
                        original_filename
                    ])
                    if restore_result['returncode'] == 0:
                        logger.info(f"✅ Successfully restored original filename")
                    else:
                        logger.warning(f"Failed to restore original filename: {restore_result['stderr']}")
                except Exception as restore_error:
                    logger.warning(f"Exception while restoring filename: {restore_error}")

        except Exception as e:
            logger.error(f"Exception in long filename download workaround: {e}")
            return False

    def _download_with_normal_flow(self, remote_path: str, local_path: str) -> bool:
        """
        使用正常流程下载文件（用于重命名后的短文件名）

        Args:
            remote_path: 远程文件路径
            local_path: 本地保存路径

        Returns:
            是否下载成功
        """
        try:
            logger.info(f"🔍 DEBUG _download_with_normal_flow: remote_path = {remote_path}")
            logger.info(f"🔍 DEBUG _download_with_normal_flow: local_path = {local_path}")
            logger.info(f"🔍 DEBUG _download_with_normal_flow: self.temp_dir = {self.temp_dir}")

            # 🔥 使用配置的temp_dir下的临时子目录，避免删除用户主目录
            temp_subdir = os.path.join(self.temp_dir, f"download_{uuid.uuid4().hex[:8]}")
            download_dir = temp_subdir

            logger.info(f"🔍 DEBUG _download_with_normal_flow: download_dir = {download_dir}")

            # 🔥 确保临时子目录存在（关键修复！）
            os.makedirs(download_dir, exist_ok=True)

            # 设置下载目录
            logger.info(f"🔍 DEBUG: Setting BaiduPCS-Go savedir to: {download_dir}")
            config_result = self._run_command(['config', 'set', '-savedir', download_dir])

            # 验证配置是否设置成功
            logger.info(f"🔍 DEBUG: Config set result: returncode={config_result['returncode']}")
            if config_result['stderr']:
                logger.info(f"🔍 DEBUG: Config set stderr: {config_result['stderr']}")
            if config_result['stdout']:
                logger.info(f"🔍 DEBUG: Config set stdout: {config_result['stdout']}")

            # 执行下载
            logger.info(f"🔍 DEBUG: Executing download command for: {remote_path}")
            result = self._run_command(['download', remote_path])

            # 检查下载命令输出
            logger.info(f"🔍 DEBUG: Download result: returncode={result['returncode']}")
            logger.info(f"🔍 DEBUG: Download stdout: {result['stdout'][:500]}...")  # 前500字符
            if result['stderr']:
                logger.info(f"🔍 DEBUG: Download stderr: {result['stderr'][:500]}...")  # 前500字符

            # 检查结果
            if result['returncode'] != 0:
                logger.error(f"Download command failed: {result['stderr']}")
                import shutil
                shutil.rmtree(download_dir, ignore_errors=True)
                return False

            # 查找下载的文件
            downloaded_file = self._find_downloaded_file(download_dir, remote_path)
            if downloaded_file and os.path.exists(downloaded_file):
                file_size = os.path.getsize(downloaded_file)
                logger.info(f"File downloaded: {remote_path} -> {downloaded_file} ({file_size} bytes)")

                # 移动文件到目标位置
                if downloaded_file != local_path:
                    target_dir = os.path.dirname(local_path)
                    if target_dir:
                        os.makedirs(target_dir, exist_ok=True)

                    try:
                        shutil.move(downloaded_file, local_path)
                        logger.info(f"Moved file to: {local_path}")
                    except Exception as e:
                        logger.error(f"Failed to move file: {e}")
                        import shutil
                        shutil.copy2(downloaded_file, local_path)
                        logger.info(f"Copied file to: {local_path}")

                # 验证文件
                if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                    # 清理临时目录
                    import shutil
                    shutil.rmtree(download_dir, ignore_errors=True)
                    return True
                else:
                    logger.error(f"File verification failed: {local_path}")
                    import shutil
                    shutil.rmtree(download_dir, ignore_errors=True)
                    return False
            else:
                logger.error(f"Downloaded file not found in {download_dir}")
                import shutil
                shutil.rmtree(download_dir, ignore_errors=True)
                return False

        except Exception as e:
            logger.error(f"Exception in normal download flow: {e}")
            import shutil
            if 'download_dir' in locals():
                shutil.rmtree(download_dir, ignore_errors=True)
            return False
