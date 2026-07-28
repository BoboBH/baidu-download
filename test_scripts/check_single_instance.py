"""
单实例检查 - 确保只有一个钉钉服务在运行 (Windows版本)
"""
import os
import sys
import msvcrt
import tempfile

def check_single_instance():
    """检查是否已有实例在运行"""
    lock_file = os.path.join(tempfile.gettempdir(), 'dingtalk_service.lock')

    try:
        # 尝试以独占模式打开文件
        fd = os.open(lock_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)

        # 写入当前进程ID
        os.write(fd, str(os.getpid()).encode())
        print(f"✅ 单实例检查通过 (PID: {os.getpid()})")
        print(f"   锁文件：{lock_file}")

        return fd

    except OSError:
        # 文件已存在，说明已有实例在运行
        try:
            with open(lock_file, 'r') as f:
                existing_pid = f.read().strip()
            print(f"❌ 错误：钉钉服务已在运行！")
            print(f"   已存在实例 PID: {existing_pid}")
            print(f"   锁文件：{lock_file}")
            print(f"\n   请先关闭其他实例：")
            print(f"   taskkill /F /PID {existing_pid}")
        except:
            print(f"❌ 错误：钉钉服务已在运行！")
            print(f"   锁文件：{lock_file}")

        return None

def release_lock(fd):
    """释放锁文件"""
    try:
        if fd:
            os.close(fd)

        lock_file = os.path.join(tempfile.gettempdir(), 'dingtalk_service.lock')
        if os.path.exists(lock_file):
            os.remove(lock_file)
            print(f"✅ 锁文件已释放")
    except Exception as e:
        print(f"⚠️  释放锁文件失败：{e}")

if __name__ == "__main__":
    fd = check_single_instance()
    if fd:
        try:
            print("模拟运行...")
            input("按 Enter 退出...")
        finally:
            release_lock(fd)
    else:
        print("❌ 已有实例在运行")
        sys.exit(1)
