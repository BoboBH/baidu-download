# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller配置文件 - 百度网盘PDF文件自动传输系统
用于将baidu-download打包为独立的Windows可执行文件

使用方法:
  pyinstaller baidu-download-simple.spec

版本: 1.6.1 (修复wxchat PDF生成问题)
"""

import os
from pathlib import Path

# 项目根目录
base_path = Path.cwd()

# ============================================================================
# 数据文件配置
# ============================================================================
datas = [
    # 配置文件模板
    ('.env.example', '.'),

    # 数据库初始化脚本
    ('release/middle/db_init.sql', 'middle'),

    # Playwright驱动文件
    ('venv/Lib/site-packages/playwright', 'playwright'),
]

# Playwright浏览器文件配置（重要！）
# 动态检测浏览器路径，支持不同用户环境
def get_playwright_browsers():
    """动态获取Playwright浏览器路径"""
    browsers = []

    # 获取当前用户路径
    user_profile = os.environ.get('USERPROFILE', 'C:\\Users\\Default')

    # 可能的浏览器路径（按优先级排序）
    possible_browsers = [
        # 当前用户的Playwright浏览器
        (os.path.join(user_profile, 'AppData', 'Local', 'ms-playwright', 'chromium-1140'), 'ms-playwright/chromium-1140'),
        (os.path.join(user_profile, 'AppData', 'Local', 'ms-playwright', 'ffmpeg-1010'), 'ms-playwright/ffmpeg-1010'),

        # 默认用户路径（打包环境）
        (r'C:\Users\Default\AppData\Local\ms-playwright\chromium-1140', 'ms-playwright/chromium-1140'),
        (r'C:\Users\Default\AppData\Local\ms-playwright\ffmpeg-1010', 'ms-playwright/ffmpeg-1010'),

        # 开发环境路径（兼容性）
        (r'C:\Users\bobo\AppData\Local\ms-playwright\chromium-1140', 'ms-playwright/chromium-1140'),
        (r'C:\Users\bobo\AppData\Local\ms-playwright\ffmpeg-1010', 'ms-playwright/ffmpeg-1010'),
    ]

    # 检查路径是否存在，添加存在的浏览器
    for browser_path, dest_path in possible_browsers:
        if os.path.exists(browser_path):
            print(f"Found Playwright browser: {browser_path}")
            browsers.append((browser_path, dest_path))
            # 只添加第一个找到的chromium，避免重复
            if 'chromium' in browser_path.lower():
                # 继续查找ffmpeg
                continue
            # 添加ffmpeg后退出
            if 'ffmpeg' in browser_path.lower():
                break

    if not browsers:
        print("Warning: No Playwright browsers found, PDF generation may fail in production")
        print("Please install browsers with: playwright install chromium")

    return browsers

# 添加浏览器文件到数据文件
playwright_browsers = get_playwright_browsers()
datas.extend(playwright_browsers)

# ============================================================================
# 隐藏导入 - PyInstaller可能无法自动检测的导入
# ============================================================================
hiddenimports = [
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

    # 项目模块
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
    'src.processor.parsers.wxchat_article_processor',
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
    ['main.py'],
    pathex=[str(base_path)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# ============================================================================
# 可执行文件配置
# ============================================================================
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='baidu-download',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
)