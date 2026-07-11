import pymysql
from typing import List, Optional
from datetime import datetime
from src.database.models import FileTransferLog, ExecutionSummary
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseRepository:
    """数据库操作仓库类"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        """
        初始化数据库连接
        
        Args:
            host: 数据库主机
            port: 数据库端口
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名称
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        
        # 创建数据库连接
        self.connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self):
        """初始化数据库和表"""
        cursor = self.connection.cursor()
        
        try:
            # 创建数据库
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database} "
                          "DEFAULT CHARACTER SET utf8mb4 "
                          "DEFAULT COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE {self.database}")
            
            # 创建表
            from src.database.models import create_tables
            sql_commands = create_tables().split(';')
            for command in sql_commands:
                command = command.strip()
                if command:
                    cursor.execute(command)
            
            self.connection.commit()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            self.connection.rollback()
            raise
        finally:
            cursor.close()
    
    def insert_file_log(self, log: FileTransferLog) -> int:
        """
        插入文件传输日志
        
        Args:
            log: 文件传输日志对象
        
        Returns:
            插入记录的ID
        """
        cursor = self.connection.cursor()
        
        try:
            sql = """
            INSERT INTO file_transfer_log 
            (share_link, extraction_code, folder_name, file_name, file_path, 
             transfer_status, start_time, file_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql, (
                log.share_link,
                log.extraction_code,
                log.folder_name,
                log.file_name,
                log.file_path,
                log.transfer_status,
                log.start_time or datetime.now(),
                log.file_size
            ))
            
            self.connection.commit()
            logger.debug(f"Inserted file log: {log.file_name}")
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"Failed to insert file log: {e}")
            self.connection.rollback()
            raise
        finally:
            cursor.close()
    
    def update_file_status(self, file_id: int, status: str, 
                         error_message: Optional[str] = None,
                         download_time: Optional[datetime] = None,
                         upload_time: Optional[datetime] = None):
        """
        更新文件传输状态
        
        Args:
            file_id: 文件记录ID
            status: 新状态
            error_message: 错误信息
            download_time: 下载完成时间
            upload_time: 上传完成时间
        """
        cursor = self.connection.cursor()
        
        try:
            sql = """
            UPDATE file_transfer_log 
            SET transfer_status = %s,
                error_message = %s,
                download_time = %s,
                upload_time = %s
            WHERE id = %s
            """
            
            cursor.execute(sql, (
                status,
                error_message,
                download_time,
                upload_time,
                file_id
            ))
            
            self.connection.commit()
            logger.debug(f"Updated file {file_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update file status: {e}")
            self.connection.rollback()
            raise
        finally:
            cursor.close()
    
    def insert_execution_summary(self, summary: ExecutionSummary) -> int:
        """
        插入执行摘要
        
        Args:
            summary: 执行摘要对象
        
        Returns:
            插入记录的ID
        """
        cursor = self.connection.cursor()
        
        try:
            sql = """
            INSERT INTO execution_summary 
            (share_link, folder_name, total_files, success_count, 
             failed_count, skipped_count, start_time, end_time, total_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql, (
                summary.share_link,
                summary.folder_name,
                summary.total_files,
                summary.success_count,
                summary.failed_count,
                summary.skipped_count,
                summary.start_time,
                summary.end_time,
                summary.total_size
            ))
            
            self.connection.commit()
            logger.info(f"Inserted execution summary for {summary.folder_name}")
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"Failed to insert execution summary: {e}")
            self.connection.rollback()
            raise
        finally:
            cursor.close()
    
    def get_file_logs_by_link(self, share_link: str) -> List[FileTransferLog]:
        """
        根据分享链接获取文件传输日志

        Args:
            share_link: 分享链接

        Returns:
            文件传输日志列表
        """
        cursor = self.connection.cursor()

        try:
            sql = """
            SELECT * FROM file_transfer_log
            WHERE share_link = %s
            ORDER BY created_at DESC
            """

            cursor.execute(sql, (share_link,))
            results = cursor.fetchall()

            logs = []
            for row in results:
                logs.append(FileTransferLog(
                    id=row['id'],
                    share_link=row['share_link'],
                    extraction_code=row['extraction_code'],
                    folder_name=row['folder_name'],
                    file_name=row['file_name'],
                    file_path=row['file_path'],
                    transfer_status=row['transfer_status'],
                    error_message=row['error_message'],
                    start_time=row['start_time'],
                    download_time=row['download_time'],
                    upload_time=row['upload_time'],
                    file_size=row['file_size'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))

            return logs

        except Exception as e:
            logger.error(f"Failed to get file logs: {e}")
            raise
        finally:
            cursor.close()

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        """支持with语句"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()
