"""
部署验证脚本 - 检查钉钉服务是否配置正确
"""
import sys
import os
from pathlib import Path

def check_imports():
    """检查必要的导入"""
    print("=== 检查Python依赖 ===")

    try:
        import dingtalk_stream
        print("OK dingtalk_stream installed")
        return True
    except ImportError as e:
        print(f"FAIL {e}")
        return False

def check_config():
    """检查配置文件"""
    print("\n=== 检查配置文件 ===")

    from dotenv import load_dotenv

    if not Path('.env').exists():
        print("FAIL .env file not found")
        print("Please create .env file with required configuration")
        return False

    load_dotenv()

    required_vars = [
        'DINGTALK_APP_KEY',
        'DINGTALK_APP_SECRET',
        'DB_HOST',
        'DB_PORT',
        'DB_USER',
        'DB_PASSWORD',
        'DB_NAME'
    ]

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
            print(f"MISSING {var}")
        else:
            # 隐藏敏感信息
            if 'SECRET' in var or 'PASSWORD' in var:
                print(f"OK {var}=***")
            else:
                print(f"OK {var}={value}")

    if missing:
        print(f"\nFAIL Missing required variables: {', '.join(missing)}")
        return False

    return True

def check_database():
    """检查数据库连接"""
    print("\n=== 检查数据库连接 ===")

    try:
        from src.config.settings import Settings
        from src.database.repository import DatabaseRepository

        settings = Settings()

        print(f"OK Database config loaded:")
        print(f"   - Host: {settings.db_host}")
        print(f"   - Port: {settings.db_port}")
        print(f"   - Database: {settings.db_name}")

        db_repo = DatabaseRepository(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name
        )

        print("OK Database connection successful")

        # 检查表结构
        cursor = db_repo.connection.cursor()
        cursor.execute("SHOW TABLES LIKE 'message_process_log'")
        result = cursor.fetchone()

        if result:
            print("OK message_process_log table exists")

            # 检查 source 字段
            cursor.execute("SHOW COLUMNS FROM message_process_log LIKE 'source'")
            source_column = cursor.fetchone()

            if source_column:
                print(f"OK source column exists: {source_column['Type']}")
            else:
                print("WARNING source column not found")
        else:
            print("WARNING message_process_log table not found")

        cursor.close()
        db_repo.close()

        return True

    except Exception as e:
        print(f"FAIL Database connection failed: {e}")
        return False

def check_dingtalk_config():
    """检查钉钉配置"""
    print("\n=== 检查钉钉配置 ===")

    try:
        from src.config.settings import Settings
        settings = Settings()

        if not settings.dingtalk_app_key:
            print("FAIL DINGTALK_APP_KEY not set")
            return False

        if not settings.dingtalk_app_secret:
            print("FAIL DINGTALK_APP_SECRET not set")
            return False

        print(f"OK DingTalk config loaded:")
        print(f"   - App Key: {settings.dingtalk_app_key}")
        print(f"   - App Secret: ***")

        return True

    except Exception as e:
        print(f"FAIL Configuration check failed: {e}")
        return False

def check_main_integration():
    """检查主程序集成"""
    print("\n=== 检查主程序集成 ===")

    try:
        # 检查 main.py 是否包含钉钉服务参数
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()

        if '--dingtalk-service' in content:
            print("OK main.py contains --dingtalk-service parameter")
        else:
            print("FAIL main.py missing --dingtalk-service parameter")
            return False

        if 'dingtalk_main' in content:
            print("OK main.py imports dingtalk service")
        else:
            print("FAIL main.py missing dingtalk service import")
            return False

        return True

    except Exception as e:
        print(f"FAIL Main integration check failed: {e}")
        return False

def main():
    """运行所有验证检查"""
    print("="*60)
    print("钉钉消息接收服务部署验证")
    print("="*60)

    results = []

    # 运行检查
    results.append(("Python依赖", check_imports()))
    results.append(("配置文件", check_config()))
    results.append(("数据库连接", check_database()))
    results.append(("钉钉配置", check_dingtalk_config()))
    results.append(("主程序集成", check_main_integration()))

    # 总结结果
    print("\n" + "="*60)
    print("验证结果总结:")

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\nSUCCESS: All checks passed! Deployment is ready.")
        print("\n启动钉钉服务:")
        print("  python main.py --dingtalk-service")
        print("  或 .exe 版本:")
        print("  baidu_transfer.exe --dingtalk-service")
        return 0
    else:
        print("\nFAILURE: Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    exit(main())
