#!/usr/bin/env python3
"""
执行数据库迁移脚本：添加消息类型支持字段
"""
import pymysql
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.config.settings import Settings
    settings = Settings()
except Exception as e:
    print(f"无法加载配置: {e}")
    sys.exit(1)

def execute_migration():
    """执行数据库迁移"""

    print("=" * 60)
    print("开始执行数据库迁移: 004_add_message_type_support.sql")
    print("=" * 60)

    try:
        # 连接数据库
        connection = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            charset='utf8mb4'
        )

        cursor = connection.cursor()

        # Phase 1: 添加 message_type 字段
        print("Phase 1: 添加 message_type 字段...")
        try:
            cursor.execute("""
                ALTER TABLE message_process_log
                ADD COLUMN message_type VARCHAR(20) DEFAULT 'baidupan' COMMENT '消息类型：baidupan/pdf_link/dingtalk_pdf/dingtalk_zip'
                AFTER source
            """)
            print("✅ message_type 字段添加成功")
        except pymysql.MySQLError as e:
            if e.args[0] == 1060:  # Duplicate column name
                print("⚠️  message_type 字段已存在，跳过")
            else:
                raise

        # Phase 2: 添加 raw_message 字段
        print("Phase 2: 添加 raw_message 字段...")
        try:
            cursor.execute("""
                ALTER TABLE message_process_log
                ADD COLUMN raw_message JSON COMMENT '原始消息内容（JSON格式）'
                AFTER message_type
            """)
            print("✅ raw_message 字段添加成功")
        except pymysql.MySQLError as e:
            if e.args[0] == 1060:
                print("⚠️  raw_message 字段已存在，跳过")
            else:
                raise

        # Phase 3: 添加 file_info 字段
        print("Phase 3: 添加 file_info 字段...")
        try:
            cursor.execute("""
                ALTER TABLE message_process_log
                ADD COLUMN file_info JSON COMMENT '文件元数据信息（JSON格式）'
                AFTER raw_message
            """)
            print("✅ file_info 字段添加成功")
        except pymysql.MySQLError as e:
            if e.args[0] == 1060:
                print("⚠️  file_info 字段已存在，跳过")
            else:
                raise

        # Phase 4: 创建索引
        print("Phase 4: 创建索引...")
        try:
            cursor.execute("""
                CREATE INDEX idx_message_type ON message_process_log(message_type)
            """)
            print("✅ idx_message_type 索引创建成功")
        except pymysql.MySQLError as e:
            if e.args[0] == 1061:  # Duplicate key name
                print("⚠️  idx_message_type 索引已存在，跳过")
            else:
                raise

        try:
            cursor.execute("""
                CREATE INDEX idx_process_status_type ON message_process_log(process_status, message_type)
            """)
            print("✅ idx_process_status_type 索引创建成功")
        except pymysql.MySQLError as e:
            if e.args[0] == 1061:
                print("⚠️  idx_process_status_type 索引已存在，跳过")
            else:
                raise

        # Phase 5: 添加约束
        print("Phase 5: 添加消息类型约束...")
        try:
            cursor.execute("""
                ALTER TABLE message_process_log
                ADD CONSTRAINT chk_message_type
                CHECK (message_type IN ('baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip'))
            """)
            print("✅ chk_message_type 约束创建成功")
        except pymysql.MySQLError as e:
            if e.args[0] == 1061:  # Duplicate constraint name
                print("⚠️  chk_message_type 约束已存在，跳过")
            else:
                raise

        # Phase 6: 更新现有记录
        print("Phase 6: 更新现有记录...")
        cursor.execute("""
            UPDATE message_process_log
            SET message_type = 'baidupan'
            WHERE message_type IS NULL OR message_type = ''
        """)
        updated_rows = cursor.rowcount
        print(f"✅ 更新了 {updated_rows} 条现有记录")

        # 提交所有更改
        connection.commit()
        print("=" * 60)
        print("🎉 数据库迁移完成！")
        print("=" * 60)

        # 验证结果
        print("\n验证迁移结果:")
        cursor.execute("""
            SELECT
                COLUMN_NAME,
                COLUMN_TYPE,
                COLUMN_DEFAULT,
                IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE
                TABLE_SCHEMA = %s
                AND TABLE_NAME = 'message_process_log'
                AND COLUMN_NAME IN ('message_type', 'raw_message', 'file_info')
            ORDER BY COLUMN_NAME
        """, (settings.db_name,))

        columns = cursor.fetchall()
        if columns:
            print("✅ 字段验证:")
            for col in columns:
                print(f"   {col[0]}: {col[1]}, DEFAULT={col[2]}, NULLABLE={col[3]}")
        else:
            print("❌ 字段验证失败")

        cursor.close()
        connection.close()

        return True

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False

if __name__ == "__main__":
    success = execute_migration()
    sys.exit(0 if success else 1)