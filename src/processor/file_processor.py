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

    def __init__(self, enable_sftp=True):
        """
        初始化处理器

        Args:
            enable_sftp: 是否启用SFTP上传（默认True）
        """
        self.settings = Settings()
        self.enable_sftp = enable_sftp

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

        # 根据enable_sftp参数决定是否连接SFTP
        if self.enable_sftp:
            if not self.sftp_client.connect():
                logger.warning("SFTP connection failed, upload will be skipped")
                self.enable_sftp = False
            else:
                logger.info("SFTP connection established")
        else:
            logger.info("SFTP upload disabled, skipping connection")

        logger.info(f"FileProcessor initialized (SFTP: {'enabled' if self.enable_sftp else 'disabled'})")

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
                    SHARE_LINK=share_link,
                    FOLDER_NAME=folder_name,
                    TOTAL_FILES=0,
                    SUCCESS_COUNT=0,
                    FAILED_COUNT=0,
                    SKIPPED_COUNT=0,
                    START_TIME=start_time,
                    END_TIME=datetime.now()
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
                SHARE_LINK=share_link,
                FOLDER_NAME=folder_name,
                TOTAL_FILES=len(pdf_files),
                SUCCESS_COUNT=success_count,
                FAILED_COUNT=failed_count,
                SKIPPED_COUNT=skipped_count,
                START_TIME=start_time,
                END_TIME=end_time,
                TOTAL_SIZE=total_size
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

        # 🔥 添加调试信息，确认remote_path不为空
        logger.debug(f"Processing file_info: {file_info}")
        logger.debug(f"Remote path from file_info: {remote_path}")

        # 🔥 关键修复：验证remote_path不为空且有效
        if not remote_path:
            logger.error(f"Empty remote_path in file_info: {file_info}")
            return 'failed'

        # 验证remote_path格式正确
        if not remote_path.startswith('//'):
            logger.warning(f"Invalid remote_path format (missing //): {remote_path}")
            # 尝试修复格式
            if remote_path.startswith('/'):
                remote_path = '/' + remote_path
            else:
                logger.error(f"Cannot fix remote_path format: {remote_path}")
                return 'failed'

        logger.info(f"Processing remote path: {remote_path[:80]}...")

        # 🔥 使用智能文件名处理：提取用户ID并缩短文件名
        from src.utils.filename_handler import FilenameHandler

        try:
            # 智能处理：生成简化文件名，保留原始文件名用于数据库
            smart_file_name, original_file_name, metadata = FilenameHandler.generate_smart_filename(remote_path)

            logger.info(f"Smart filename processing: {original_file_name[:50]}... -> {smart_file_name}")
            logger.debug(f"Metadata: {metadata}")

            # 使用简化文件名进行SFTP上传，但保留原始文件名在数据库中
            sftp_file_name = smart_file_name

        except Exception as e:
            logger.warning(f"Smart filename processing failed: {e}, using original name")
            # 降级到原始处理方式
            if '/' in remote_path:
                parts = remote_path.split('/')
                for part in reversed(parts):
                    if part and part.endswith('.pdf'):
                        original_file_name = part
                        break
                else:
                    original_file_name = parts[-1] if parts else "unknown.pdf"
            else:
                original_file_name = os.path.basename(remote_path)

            sftp_file_name = original_file_name

        # 确保文件名不为空
        if not original_file_name:
            original_file_name = "unknown.pdf"

        # 使用极短的临时文件名避免文件名长度限制问题
        # 按用户建议使用简单的文件名：temp_a.pdf, temp_b.pdf, temp_c.pdf...
        if not hasattr(self, '_temp_counter'):
            self._temp_counter = 0

        # 生成简单的临时文件名：temp_a.pdf, temp_b.pdf, ..., temp_z.pdf, temp_aa.pdf
        temp_id = self._temp_counter
        self._temp_counter += 1

        # 转换为字母序列：0->a, 1->b, ..., 25->z, 26->aa, 27->ab, ...
        def id_to_alpha(id):
            result = ""
            while id >= 0:
                result = chr(ord('a') + (id % 26)) + result
                id = id // 26 - 1
                if id < 0:
                    break
            return result if result else "a"

        temp_suffix = id_to_alpha(temp_id)
        temp_file_name = f"temp_{temp_suffix}.pdf"
        local_path = os.path.join(self.temp_dir, temp_file_name)

        logger.info(f"Processing file: {original_file_name}")
        logger.debug(f"Remote path: {remote_path}")
        logger.debug(f"Original file name: {original_file_name}")
        logger.debug(f"Temp file name: {temp_file_name}")
        logger.debug(f"Local path: {local_path}")

        # ===== 去重检查：检查文件是否已经成功上传 =====
        existing_log = self.db_repo.get_file_log_by_name_and_link(
            file_name=original_file_name,
            share_link=share_link,
            folder_name=folder_name
        )

        if existing_log and existing_log.TRANSFER_STATUS == 'success':
            # 检查是否需要重新上传：
            # 1. 如果当前启用SFTP但之前没有upload_time，说明之前是--no-sftp模式，需要重新上传
            # 2. 如果当前禁用SFTP且之前有upload_time，说明之前是SFTP模式，但现在不需要上传，可以跳过
            # 3. 如果当前启用SFTP且之前有upload_time，说明已经上传过，可以跳过
            should_skip = False

            if self.enable_sftp:
                # 启用SFTP模式：只有当之前真正上传过（有upload_time）时才跳过
                if existing_log.UPLOAD_TIME is not None:
                    logger.info(f"File already uploaded to SFTP: {original_file_name}")
                    logger.info(f"Previous upload time: {existing_log.UPLOAD_TIME}")
                    logger.info(f"Skipping download and upload")
                    should_skip = True
                else:
                    logger.info(f"File was processed in --no-sftp mode (no upload_time): {original_file_name}")
                    logger.info(f"Will upload to SFTP this time")
                    # 继续处理，会重新下载并上传
            else:
                # 禁用SFTP模式：无论之前是否上传过，都可以跳过
                logger.info(f"File already processed (SFTP disabled): {original_file_name}")
                logger.info(f"Skipping download and upload")
                should_skip = True

            if should_skip:
                return 'skipped'
        elif existing_log and existing_log.TRANSFER_STATUS == 'uploading':
            logger.warning(f"File is currently being uploaded: {original_file_name}")
            logger.info(f"Skipping to avoid duplicate operations")
            return 'skipped'  # 跳过正在上传的文件
        elif existing_log:
            # 对于失败、下载中、待处理等状态，需要重新下载并上传
            logger.info(f"File exists in database with status: {existing_log.TRANSFER_STATUS}")
            logger.info(f"Will re-download and retry upload for: {original_file_name}")
            # 继续处理，会重新下载文件
        else:
            logger.debug(f"No existing log found for: {original_file_name}")

        # ===== 插入新的文件日志 =====

        # 插入文件日志（使用原始文件名）
        file_log = FileTransferLog(
            SHARE_LINK=share_link,
            EXTRACTION_CODE=code,
            FOLDER_NAME=folder_name,
            FILE_NAME=original_file_name,  # 使用原始文件名
            FILE_PATH=remote_path,
            TRANSFER_STATUS='pending',
            START_TIME=datetime.now(),
            FILE_SIZE=file_info['size']
        )

        log_id = self.db_repo.insert_file_log(file_log)

        # 尝试下载
        for attempt in range(self.max_retries):
            logger.info(f"Downloading {original_file_name} to {temp_file_name} (attempt {attempt + 1}/{self.max_retries})")

            # 更新状态为downloading
            self.db_repo.update_file_status(log_id, 'downloading')

            if self.baidu_client.download_file(remote_path, local_path):
                logger.info(f"Downloaded: {original_file_name} -> {temp_file_name}")
                break
            elif attempt == self.max_retries - 1:
                # 最后一次尝试失败
                error_msg = f"Download failed after {self.max_retries} attempts"
                logger.error(f"{error_msg}: {original_file_name}")
                self.db_repo.update_file_status(log_id, 'failed', error_msg)
                return 'failed'

        # 尝试上传（使用原始文件名）- 根据enable_sftp参数决定
        download_time = datetime.now()

        if not self.enable_sftp:
            # SFTP上传被禁用，直接标记为成功（不设置upload_time，因为没有上传操作）
            logger.info(f"SFTP upload disabled, marking {original_file_name} as success")
            self.db_repo.update_file_status(
                log_id, 'success',
                download_time=download_time
                # 不设置upload_time，因为没有实际的SFTP上传操作
            )

            # 删除本地临时文件
            self._delete_local_file(local_path)

            logger.info(f"Successfully processed (no SFTP upload): {original_file_name}")
            return 'success'

        # 启用SFTP上传
        self.db_repo.update_file_status(log_id, 'uploading', download_time=download_time)

        remote_upload_path = os.path.join(
            self.sftp_client.remote_path,
            folder_name,
            sftp_file_name  # 使用处理后的文件名上传
        ).replace('\\', '/')

        logger.info(f"Uploading {original_file_name} to SFTP...")
        logger.debug(f"Local file: {local_path}")
        logger.debug(f"Remote path: {remote_upload_path}")
        logger.debug(f"SFTP server: {self.sftp_client.host}:{self.sftp_client.port}")

        # 确保远程目录存在
        remote_dir = os.path.dirname(remote_upload_path)
        if not self.sftp_client.create_directory(remote_dir):
            logger.error(f"Failed to create remote directory: {remote_dir}")
            self.db_repo.update_file_status(
                log_id, 'failed',
                "Failed to create remote directory",
                download_time=download_time
            )
            # 删除本地临时文件（目录创建失败是致命错误，无法重试）
            self._delete_local_file(local_path)
            return 'failed'

        if self.sftp_client.upload_file(local_path, remote_upload_path):
            # 上传成功
            upload_time = datetime.now()
            self.db_repo.update_file_status(
                log_id, 'success',
                download_time=download_time,
                upload_time=upload_time  # 只有在真正上传成功时才设置
            )

            # 删除本地临时文件
            self._delete_local_file(local_path)

            logger.info(f"Successfully processed: {original_file_name}")
            return 'success'
        else:
            # 上传失败
            error_msg = "Upload failed"
            self.db_repo.update_file_status(
                log_id, 'failed',
                error_msg,
                download_time=download_time
                # 不设置upload_time，因为上传没有成功
            )

            # 删除部分下载的文件（上传失败可能需要重试，但暂时删除）
            self._delete_local_file(local_path)

            logger.error(f"Upload failed: {original_file_name}")
            return 'failed'

    def _delete_local_file(self, file_path: str):
        """删除本地临时文件"""
        try:
            if not file_path or file_path.endswith(os.sep) or file_path.endswith('/'):
                logger.warning(f"Invalid file path for deletion: {file_path}")
                return

            file_path_obj = Path(file_path)
            if file_path_obj.exists() and file_path_obj.is_file():
                os.remove(file_path)
                logger.debug(f"Deleted local file: {file_path}")
            elif file_path_obj.exists() and file_path_obj.is_dir():
                logger.warning(f"Path is directory, not file: {file_path}")
            else:
                logger.debug(f"File does not exist, skip deletion: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete local file: {e}")

    def _cleanup_temp_files(self):
        """清理临时目录"""
        try:
            # 清理配置的临时目录
            temp_path = Path(self.temp_dir)
            if temp_path.exists():
                # 删除临时目录中的所有文件
                for file in temp_path.glob('*'):
                    if file.is_file():
                        file.unlink()
                        logger.debug(f"Cleaned up temp file: {file}")

            # 清理BaiduPCS-Go的默认下载目录
            download_dir = Path("download")
            if download_dir.exists():
                for file in download_dir.glob('*'):
                    if file.is_file():
                        file.unlink()
                        logger.debug(f"Cleaned up download file: {file}")
                # 删除空的download目录
                try:
                    download_dir.rmdir()
                    logger.info("Cleaned up BaiduPCS-Go download directory")
                except:
                    pass

            logger.info("Temporary files cleanup completed")
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
