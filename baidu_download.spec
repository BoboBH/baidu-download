# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller配置文件 - 百度网盘PDF文件自动传输系统
用于将baidu-download打包为独立的Windows可执行文件

使用方法:
  pyinstaller baidu_download.spec

构建要求:
  - Python 3.8+
  - PyInstaller: pip install pyinstaller
  - 所有项目依赖项: pip install -r requirements.txt

作者: baidu-download team
版本: 1.1.5
"""

import os
import sys
from pathlib import Path

# 项目根目录
base_path = Path.cwd()

# ============================================================================
# 数据文件配置 - 包含所有运行时需要的非Python文件
# ============================================================================
datas = [
    # 配置文件模板
    (base_path / '.env.example', '.'),

    # 数据库初始化脚本
    (base_path / 'middle' / 'db_init.sql', 'middle'),

    # 百度网盘CLI工具 (如果存在)
    (base_path / 'BaiduPCS-Go.exe', '.'),
]

# 添加所有源代码目录 - PyInstaller需要这些来正确分析导入
# 格式: (源路径, 目标路径)
datas += [
    (base_path / 'src', 'src'),
]

# ============================================================================
# 隐藏导入 - PyInstaller可能无法自动检测的导入
# ============================================================================
hidden_imports = [
    # 核心依赖
    'paramiko',
    'pysftp',
    'pymysql',
    'dotenv',
    'colorama',
    'requests',

    # 项目模块 (确保所有src模块都被包含)
    'src.config.settings',
    'src.database.models',
    'src.database.repository',
    'src.database.message_models',
    'src.downloader.baidu_client',
    'src.uploader.sftp_client',
    'src.feishu.feishu_client',
    'src.feishu.message_parser',
    'src.notification.dingtalk_notifier',
    'src.processor.file_processor',
    'src.processor.auto_processor',
    'src.utils.logger',
    'src.utils.filename_handler',
    'src.utils.resource_utils',
]

# ============================================================================
# 分析配置
# ============================================================================
a = Analysis(
    ['main.py'],  # 主入口点
    pathex=[str(base_path)],  # 搜索路径
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的标准库模块以减小文件大小
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'IPython',
        'notebook',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# ============================================================================
# 过滤配置 - 移除不需要的文件
# ============================================================================
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# ============================================================================
# 可执行文件配置
# ============================================================================
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='baidu-download',  # 可执行文件名称
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 使用UPX压缩 (如果可用)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 控制台应用程序 (显示日志输出)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,

    # Windows可执行文件元数据
    version=None,  # 可以添加version info文件
    icon=None,     # 可以添加.ico图标文件
)

# ============================================================================
# 版本信息配置 (可选)
# ============================================================================
# 要启用版本信息，需要创建一个version.txt文件并取消下面的注释:
#
# version_info = {
#     'version': '1.1.5',
#     'description': '百度网盘PDF文件自动传输系统',
#     'company': 'baidu-download team',
#     'product': 'Baidu Download Manager',
#     'copyright': 'Copyright © 2026',
#     'trademarks': '',
#     'file_version': '1.1.5.0',
#     'product_version': '1.1.5.0',
# }
#
# exe = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     [],
#     name='baidu-download',
#     version='version_info.txt',  # 需要使用PyInstaller的命令行工具创建
#     # ... 其他参数保持不变
# )