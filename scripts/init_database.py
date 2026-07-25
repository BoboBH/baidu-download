#!/usr/bin/env python3
"""
数据库初始化脚本
根据 .env 配置文件中的设置自动创建和初始化数据库
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.database.models import create_tables
from src.utils.logger import get_logger
import pymysql

logger = get_logger(__name__)

def init_database():
    """初始化数据库"""
    try:
        # 加载配置
        settings = Settings()
        logger.info(f"正在初始化数据库: {settings.db_name}")

        # 连接MySQL (不指定数据库)
        connection = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        cursor = connection.cursor()

        try:
            # 生成创建表的SQL
            sql_commands = create_tables(settings.db_name).split(';')

            for command in sql_commands:
                command = command.strip()
                if command and not command.startswith('--'):
                    logger.info(f"执行SQL: {command[:50]}...")
                    cursor.execute(command)

            connection.commit()
            logger.info(f"✅ 数据库 '{settings.db_name}' 初始化成功！")

            # 显示创建的表
            cursor.execute(f"USE {settings.db_name}")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

            print("\n创建的表:")
            for table in tables:
                table_name = list(table.values())[0]
                print(f"  - {table_name}")

            return True

        except Exception as e:
            connection.rollback()
            logger.error(f"❌ 数据库初始化失败: {e}")
            return False

        finally:
            cursor.close()
            connection.close()

    except Exception as e:
        logger.error(f"❌ 配置加载或连接失败: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)