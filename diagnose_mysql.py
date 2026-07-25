"""
MySQL连接诊断工具
"""
import pymysql
import sys

def diagnose_mysql():
    """诊断MySQL连接问题"""
    print("=== MySQL Connection Diagnostic Tool ===")
    print()

    try:
        # 尝试连接MySQL服务器（不指定数据库）
        print("1. Testing MySQL server connection...")
        connection = pymysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='123456',
            charset='utf8mb4'
        )

        print("SUCCESS: MySQL server connected!")

        # 获取MySQL版本
        cursor = connection.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"MySQL Version: {version}")

        # 检查root用户的认证方式
        cursor.execute("SELECT user, host, plugin FROM mysql.user WHERE user='root'")
        users = cursor.fetchall()

        print(f"\n2. Root user authentication method:")
        for user in users:
            print(f"   User: {user[0]}@{user[1]}, Plugin: {user[2]}")

        # 检查test数据库是否存在
        cursor.execute("SHOW DATABASES LIKE 'test'")
        test_db_exists = cursor.fetchone()

        if test_db_exists:
            print(f"\nSUCCESS: test database exists")
        else:
            print(f"\nWARNING: test database does not exist")

        cursor.close()
        connection.close()

        # 诊断结果
        print(f"\n=== Diagnostic Results ===")

        if "8." in version:
            print("DETECTED: MySQL 8.0 - authentication compatibility issue")
            print("SOLUTION:")
            print("   1. Change root user authentication to mysql_native_password")
            print("   2. Or create new user with old authentication method")

            return "mysql_8_issue"
        else:
            print("OK: MySQL version compatible, password might be wrong")
            return "password_error"

    except pymysql.err.OperationalError as e:
        error_code = e.args[0]
        if error_code == 1045:
            print(f"ERROR: Authentication failed: {e}")
            print("Possible causes:")
            print("   1. Wrong password")
            print("   2. User does not exist")
            print("   3. MySQL 8.0 authentication incompatibility")
            return "auth_failed"
        else:
            print(f"ERROR: Connection error: {e}")
            return "connection_error"
    except Exception as e:
        print(f"ERROR: Diagnostic process failed: {e}")
        return "diagnostic_error"

if __name__ == "__main__":
    result = diagnose_mysql()

    print(f"\n=== Recommended Solutions ===")

    if result == "mysql_8_issue":
        print("""
Solution 1: Modify root user authentication (Recommended)
----------------------------------------------------------
Execute the following SQL in MySQL:

ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';
FLUSH PRIVILEGES;

Solution 2: Create new user with old authentication
---------------------------------------------------
CREATE USER 'baidu'@'localhost' IDENTIFIED WITH mysql_native_password BY 'your_password';
GRANT ALL PRIVILEGES ON *.* TO 'baidu'@'localhost';
FLUSH PRIVILEGES;

Then modify .env file to use new user:
DB_USER=baidu
DB_PASSWORD=your_password
        """)
    elif result == "password_error":
        print("""
Please check:
1. Is DB_PASSWORD in .env file correct?
2. What is the password for root user in MySQL?
3. Try resetting password in MySQL:

ALTER USER 'root'@'localhost' IDENTIFIED BY 'your_password';
FLUSH PRIVILEGES;
        """)