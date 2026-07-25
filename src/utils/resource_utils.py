import os
import sys
from pathlib import Path

def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径
    支持开发环境和PyInstaller打包后的单文件环境

    Args:
        relative_path: 相对路径

    Returns:
        资源文件的绝对路径
    """
    try:
        # PyInstaller创建临时文件夹将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except AttributeError:
        # 正常开发环境
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_executable_dir():
    """
    获取可执行文件所在目录

    Returns:
        可执行文件所在目录的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # 打包后的环境
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.abspath(".")

def ensure_path_exists(path):
    """
    确保路径存在，如果不存在则创建

    Args:
        path: 文件或目录路径
    """
    path_obj = Path(path)
    if path_obj.suffix:
        # 文件路径
        path_obj.parent.mkdir(parents=True, exist_ok=True)
    else:
        # 目录路径
        path_obj.mkdir(parents=True, exist_ok=True)