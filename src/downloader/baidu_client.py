import subprocess
import os
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

            result = self._run_command([
                'login',
                '--cookies', self.cookies_path
            ])

            if result['returncode'] == 0:
                logger.info("Login successful")
                return True
            else:
                logger.error(f"Login failed: {result['stderr']}")
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
            result = self._run_command([
                'share',
                'save',
                share_link,
                code,
                '-p', f'/{folder_name}'
            ])

            if result['returncode'] == 0:
                logger.info(f"Share link saved to /{folder_name}")
                return True
            else:
                logger.error(f"Save share link failed: {result['stderr']}")
                return False

        except Exception as e:
            logger.error(f"Save share link exception: {e}")
            return False

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
                f'/{folder_name}'
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
                f'/{folder_name}'
            ])

            if result['returncode'] != 0:
                logger.error(f"List files failed: {result['stderr']}")
                return []

            # 解析输出，找出PDF文件
            pdf_files = []
            for line in result['stdout'].split('\n'):
                line = line.strip()
                if not line:
                    continue

                # BaiduPCS-Go输出格式：- 路径 大小
                # 例如：- /test.pdf 1048576
                parts = line.split()
                if len(parts) >= 3 and parts[0] == '-':
                    file_path = parts[1]  # 路径部分
                    file_size = parts[2]  # 大小部分

                    # 只处理PDF文件
                    if file_path.lower().endswith('.pdf'):
                        pdf_files.append({
                            'name': file_path,
                            'size': int(file_size) if file_size.isdigit() else 0
                        })

            logger.info(f"Found {len(pdf_files)} PDF files in /{folder_name}")
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
            os.makedirs(local_dir, exist_ok=True)

            result = self._run_command([
                'download',
                remote_path,
                '--save', local_path
            ])

            if result['returncode'] == 0:
                logger.info(f"File downloaded: {remote_path} -> {local_path}")
                return True
            else:
                logger.error(f"Download failed: {result['stderr']}")
                return False

        except Exception as e:
            logger.error(f"Download exception: {e}")
            return False
