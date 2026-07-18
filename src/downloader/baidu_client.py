import subprocess
import os
import re
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

            # 🔥 关键修复：使用固定的download目录，避免路径过长问题
            # BaiduPCS-Go会保持原始目录结构，导致超长路径问题
            # 我们让它下载到专门的download目录，然后我们手动处理
            download_dir = "download"

            # 使用配置的savedir，设置为download目录
            self._run_command(['config', 'set', '-savedir', download_dir])

            logger.debug(f"Downloading {remote_path} to {download_dir}")

            result = self._run_command([
                'download',
                remote_path
            ])

            if result['returncode'] == 0:
                # BaiduPCS-Go 会将文件下载到配置的savedir
                # 文件名可能与原始名称不同（特别是中文或特殊字符）
                # 我们需要查找最新下载的文件

                downloaded_file = self._find_downloaded_file(download_dir, remote_path)
                if downloaded_file and os.path.exists(downloaded_file):
                    file_size = os.path.getsize(downloaded_file)
                    logger.info(f"File downloaded: {remote_path} -> {downloaded_file} ({file_size} bytes)")

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
                        return True
                    else:
                        logger.error(f"Downloaded file is empty or missing: {local_path}")
                        return False
                else:
                    logger.error(f"Download command succeeded but file not found in {temp_dir}")
                    logger.debug(f"Expected file at: {local_path}")
                    logger.debug(f"Download output: {result['stdout']}")
                    return False
            else:
                logger.error(f"Download command failed: {result['stderr']}")
                logger.debug(f"Download stdout: {result['stdout']}")
                return False

        except Exception as e:
            logger.error(f"Download exception: {e}")
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
