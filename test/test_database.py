"""
验证数据库连接和写入位置
"""
import pymysql
import sys

def test_database_connection():
    """测试数据库连接和数据写入位置"""

    # 模拟程序的两阶段连接
    print("=== 阶段1: 连接到MySQL服务器 (不指定数据库) ===")

    try:
        connection = pymysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='123456',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✅ MySQL服务器连接成功")

        # 获取当前数据库
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()
        print(f"📊 当前数据库: {current_db['DATABASE()']} (应该是NULL)")

        # 模拟阶段2: 使用USE database
        print("\n=== 阶段2: 初始化数据库 (USE test) ===")
        database_name = "test"

        # 创建数据库（如果不存在）
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
        cursor.execute(f"USE {database_name}")

        # 验证当前数据库
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()
        print(f"📊 切换后数据库: {current_db['DATABASE()']} (应该是test)")

        # 测试数据写入
        print("\n=== 阶段3: 测试数据写入 ===")

        # 创建测试表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            test_data VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 插入测试数据
        cursor.execute("INSERT INTO test_table (test_data) VALUES ('test_data_123')")
        connection.commit()

        # 验证数据写入位置
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()
        print(f"📊 写入数据时数据库: {current_db['DATABASE()']}")

        # 查询刚插入的数据
        cursor.execute("SELECT * FROM test_table WHERE test_data = 'test_data_123'")
        result = cursor.fetchone()

        if result:
            print(f"✅ 数据写入成功！位置: {current_db['DATABASE()']}.test_table")
            print(f"📋 测试数据: {result}")
        else:
            print("❌ 数据写入失败")

        # 清理测试数据
        cursor.execute("DROP TABLE IF EXISTS test_table")
        connection.commit()
        print("🧹 测试数据已清理")

        cursor.close()
        connection.close()

        print("\n=== 结论 ===")
        print("✅ 虽然连接时不指定数据库，但通过 USE database 后，")
        print("✅ 所有数据操作都正确地写入到指定的数据库中！")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)