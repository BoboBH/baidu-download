import pysftp
import os
from pathlib import Path
from typing import Optional, Dict
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class SFTPClient:
    """SFTP客户端，处理文件上传操作"""

    def __init__(self, custom_config: Optional[Dict] = None):
        """
        初始化客户端

        Args:
            custom_config: 自定义SFTP配置，包含:
                         - host: SFTP主机
                         - port: SFTP端口
                         - username: 用户名
                         - password: 密码
                         - remote_path: 远程路径 (可选)
                         如果为None，使用默认配置
        """
        if custom_config:
            # 使用自定义配置
            self.host = custom_config.get('host')
            self.port = custom_config.get('port', 22)
            self.username = custom_config.get('username')
            self.password = custom_config.get('password')
            self.remote_path = custom_config.get('remote_path', '')
            self.use_custom_config = True
        else:
            # 使用默认配置
            self.settings = Settings()
            self.host = self.settings.sftp_host
            self.port = self.settings.sftp_port
            self.username = self.settings.sftp_username
            self.password = self.settings.sftp_password
            self.remote_path = self.settings.sftp_remote_path
            self.use_custom_config = False

        self.sftp: Optional[pysftp.Connection] = None

        logger.info(f"SFTPClient initialized for {self.host}:{self.port}")

    def connect(self) -> bool:
        """
        连接到SFTP服务器

        Returns:
            是否连接成功
        """
        try:
            # 创建CnOpts并禁用主机密钥检查（适用于内部可信SFTP服务器）
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None

            self.sftp = pysftp.Connection(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                cnopts=cnopts
            )

            logger.info(f"Connected to SFTP server: {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"SFTP connection failed: {e}")
            return False

    def disconnect(self):
        """断开SFTP连接"""
        if self.sftp:
            self.sftp.close()
            self.sftp = None
        logger.info("Disconnected from SFTP server")

    def create_directory(self, dir_path: str) -> bool:
        """
        创建远程目录

        Args:
            dir_path: 目录路径

        Returns:
            是否创建成功
        """
        try:
            if not self.sftp:
                logger.error("Not connected to SFTP server")
                return False

            # 检查目录是否存在，不存在则递归创建
            try:
                self.sftp.stat(dir_path)
                logger.debug(f"Directory exists: {dir_path}")
                return True
            except IOError:
                # 目录不存在，递归创建
                dirs = []
                current = dir_path
                while current != '/':
                    try:
                        self.sftp.stat(current)
                        break  # 找到存在的目录
                    except IOError:
                        dirs.append(current)
                        current = os.path.dirname(current)

                # 从上到下创建目录
                for dir_path in reversed(dirs):
                    self.sftp.mkdir(dir_path)
                    logger.info(f"Directory created: {dir_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to create directory: {e}")
            return False

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        上传文件到SFTP服务器

        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径

        Returns:
            是否上传成功
        """
        try:
            if not self.sftp:
                logger.error("Not connected to SFTP server")
                return False

            # 检查本地文件是否存在
            if not Path(local_path).exists():
                logger.error(f"Local file not found: {local_path}")
                return False

            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_path)
            if remote_dir and not self.create_directory(remote_dir):
                return False

            # 上传文件
            self.sftp.put(local_path, remote_path)

            # 验证上传
            try:
                self.sftp.stat(remote_path)
                logger.info(f"File uploaded successfully: {local_path} -> {remote_path}")
                return True
            except IOError:
                logger.error(f"Upload verification failed: {remote_path}")
                return False

        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return False

    def __enter__(self):
        """支持with语句"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.disconnect()
