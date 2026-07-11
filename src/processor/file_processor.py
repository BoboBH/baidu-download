import os
from datetime import datetime
from typing import Optional
from pathlib import Path

from src.downloader.baidu_client import BaiduClient
from src.uploader.sftp_client import SFTPClient
from src.database.repository import DatabaseRepository
from src.database.models import FileTransferLog, ExecutionSummary
from src.config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class FileProcessor:
    """文件处理协调器，协调整个文件传输流程"""

    def __init__(self):
        """初始化处理器"""
        self.settings = Settings()

        # 初始化各个组件
        self.baidu_client = BaiduClient()
        self.sftp_client = SFTPClient()
        self.db_repo = DatabaseRepository(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name
        )

        self.temp_dir = self.settings.temp_dir
        self.max_retries = self.settings.max_retries

        logger.info("FileProcessor initialized")

    def process_files(self, share_link: str, code: str, folder_name: str) -> Optional[ExecutionSummary]:
        """
        处理文件传输的完整流程

        Args:
            share_link: 百度网盘分享链接
            code: 提取码
            folder_name: 目标目录名

        Returns:
            执行摘要，如果失败返回None
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting file processing for folder: {folder_name}")

            # 1. 登录百度网盘
            if not self.baidu_client.login():
                logger.error("Baidu login failed")
                return None

            # 2. 删除已存在的目录
            logger.info(f"Deleting existing directory if exists: /{folder_name}")
            self.baidu_client.delete_directory(folder_name)

            # 3. 转存分享链接
            logger.info(f"Saving share link to /{folder_name}")
            if not self.baidu_client.save_share_link(share_link, code, folder_name):
                logger.error("Failed to save share link")
                return None

            # 4. 获取PDF文件列表
            logger.info("Listing PDF files...")
            pdf_files = self.baidu_client.list_pdf_files(folder_name)

            if not pdf_files:
                logger.warning("No PDF files found")
                return ExecutionSummary(
                    share_link=share_link,
                    folder_name=folder_name,
                    total_files=0,
                    success_count=0,
                    failed_count=0,
                    skipped_count=0,
                    start_time=start_time,
                    end_time=datetime.now()
                )

            logger.info(f"Found {len(pdf_files)} PDF files")

            # 5. 处理每个文件
            success_count = 0
            failed_count = 0
            skipped_count = 0
            total_size = 0

            for file_info in pdf_files:
                result = self._process_single_file(
                    file_info=file_info,
                    share_link=share_link,
                    code=code,
                    folder_name=folder_name
                )

                if result == 'success':
                    success_count += 1
                    total_size += file_info['size']
                elif result == 'failed':
                    failed_count += 1
                else:  # skipped
                    skipped_count += 1

            # 6. 创建执行摘要
            end_time = datetime.now()
            summary = ExecutionSummary(
                share_link=share_link,
                folder_name=folder_name,
                total_files=len(pdf_files),
                success_count=success_count,
                failed_count=failed_count,
                skipped_count=skipped_count,
                start_time=start_time,
                end_time=end_time,
                total_size=total_size
            )

            # 7. 保存执行摘要
            self.db_repo.insert_execution_summary(summary)

            logger.info(f"Processing completed: {success_count} success, {failed_count} failed, {skipped_count} skipped")

            return summary

        except Exception as e:
            logger.error(f"File processing failed: {e}")
            return None
        finally:
            # 清理临时文件
            self._cleanup_temp_files()

    def _process_single_file(self, file_info: dict, share_link: str,
                           code: str, folder_name: str) -> str:
        """
        处理单个文件

        Args:
            file_info: 文件信息字典，包含name和size
            share_link: 分享链接
            code: 提取码
            folder_name: 目录名

        Returns:
            处理结果: 'success', 'failed', 'skipped'
        """
        remote_path = file_info['name']
        file_name = os.path.basename(remote_path)
        local_path = os.path.join(self.temp_dir, file_name)

        # 插入文件日志
        file_log = FileTransferLog(
            share_link=share_link,
            extraction_code=code,
            folder_name=folder_name,
            file_name=file_name,
            file_path=remote_path,
            transfer_status='pending',
            start_time=datetime.now(),
            file_size=file_info['size']
        )

        log_id = self.db_repo.insert_file_log(file_log)

        # 尝试下载
        for attempt in range(self.max_retries):
            logger.info(f"Downloading {file_name} (attempt {attempt + 1}/{self.max_retries})")

            # 更新状态为downloading
            self.db_repo.update_file_status(log_id, 'downloading')

            if self.baidu_client.download_file(remote_path, local_path):
                logger.info(f"Downloaded: {file_name}")
                break
            elif attempt == self.max_retries - 1:
                # 最后一次尝试失败
                error_msg = f"Download failed after {self.max_retries} attempts"
                logger.error(f"{error_msg}: {file_name}")
                self.db_repo.update_file_status(log_id, 'failed', error_msg)
                return 'failed'

        # 尝试上传
        download_time = datetime.now()
        self.db_repo.update_file_status(log_id, 'uploading', download_time=download_time)

        remote_upload_path = os.path.join(
            self.sftp_client.remote_path,
            folder_name,
            file_name
        ).replace('\\', '/')

        if self.sftp_client.upload_file(local_path, remote_upload_path):
            # 上传成功
            upload_time = datetime.now()
            self.db_repo.update_file_status(
                log_id, 'success',
                download_time=download_time,
                upload_time=upload_time
            )

            # 删除本地临时文件
            self._delete_local_file(local_path)

            logger.info(f"Successfully processed: {file_name}")
            return 'success'
        else:
            # 上传失败
            error_msg = "Upload failed"
            self.db_repo.update_file_status(
                log_id, 'failed',
                error_msg,
                download_time=download_time
            )

            # 删除部分下载的文件
            self._delete_local_file(local_path)

            logger.error(f"Upload failed: {file_name}")
            return 'failed'

    def _delete_local_file(self, file_path: str):
        """删除本地临时文件"""
        try:
            if Path(file_path).exists():
                os.remove(file_path)
                logger.debug(f"Deleted local file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete local file: {e}")

    def _cleanup_temp_files(self):
        """清理临时目录"""
        try:
            temp_path = Path(self.temp_dir)
            if temp_path.exists():
                # 删除临时目录中的所有文件
                for file in temp_path.glob('*'):
                    if file.is_file():
                        file.unlink()
                        logger.debug(f"Cleaned up temp file: {file}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")

    def close(self):
        """关闭所有连接"""
        try:
            self.sftp_client.disconnect()
            self.db_repo.close()
            logger.info("All connections closed")
        except Exception as e:
            logger.error(f"Error closing connections: {e}")

    def __enter__(self):
        """支持with语句"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()
