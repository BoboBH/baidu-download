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
版本: 1.4.2
"""

import os
import sys
from pathlib import Path

# 项目根目录
base_path = Path.cwd()

# 设置输出目录到 release/dist
dist_path = base_path / 'release' / 'dist'
work_path = base_path / 'build'
if not dist_path.exists():
    dist_path.mkdir(parents=True, exist_ok=True)

# ============================================================================
# 数据文件配置 - 包含所有运行时需要的非Python文件
# ============================================================================
datas = [
    # 配置文件模板
    (base_path / '.env.example', '.'),

    # 数据库初始化脚本
    (base_path / 'middle' / 'db_init.sql', 'middle'),

    # 微信文章处理数据库脚本
    (base_path / 'database' / 'wxchat_tables.sql', 'database'),

    # 数据库迁移脚本（包含所有迁移文件）
    (base_path / 'database' / 'migrations' / 'migrate_add_source_field.sql', 'database/migrations'),
    (base_path / 'database' / 'migrations' / 'migrate_rename_wxchat_tables.sql', 'database/migrations'),

    # 百度网盘CLI工具 (如果存在)
    (base_path / 'BaiduPCS-Go.exe', '.'),

    # 百度网盘cookies文件 (重要！用于百度网盘登录认证)
    (base_path / 'baidu-cookies.txt', '.'),

    # Playwright驱动文件
    (base_path / 'venv/Lib/site-packages/playwright', 'playwright'),

    # Playwright浏览器文件（重要！这会让exe增加约300MB）
    # 使用最新版本的Chromium和FFmpeg以确保最佳性能和兼容性
    (r'C:\Users\bobo\AppData\Local\ms-playwright\chromium-1223', r'ms-playwright\chromium-1223'),
    (r'C:\Users\bobo\AppData\Local\ms-playwright\ffmpeg-1011', r'ms-playwright\ffmpeg-1011'),
]

# 注意: PyInstaller会自动包含所有被导入的Python模块
# src/目录中的模块会通过import语句自动包含，无需手动指定

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
    'dingtalk_stream',
    'asyncio',
    'playwright',
    'playwright.sync_api',

    # PDF生成依赖 (仅使用Playwright)
    # 移除了reportlab和PIL依赖，只使用playwright

    # 项目模块 (确保所有src模块都被包含)
    'src.config.settings',
    'src.database.models',
    'src.database.repository',
    'src.database.message_models',
    'src.downloader.baidu_client',
    'src.uploader.sftp_client',
    'src.feishu.feishu_client',
    'src.feishu.message_parser',
    'src.feishu.dingtalk_group_client',
    'src.notification.dingtalk_notifier',
    'src.processor.file_processor',
    'src.processor.auto_processor',
    'src.processor.message_receiver',
    'src.processor.file_transfer_processor',
    'src.wxchat.models',
    'src.wxchat.processor',
    'src.wxchat.commands',
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
        # 注意：不能排除PIL，因为reportlab需要它
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
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
    version='version_info.txt',  # 版本信息文件
    icon='baidu-download.ico',  # 应用程序图标文件
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