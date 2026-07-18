@echo off
setlocal enabledelayedexpansion

REM ==========================================
REM 百度网盘PDF文件自动传输系统 - 智能数据库初始化脚本
REM 自动读取.env文件中的DB_NAME配置
REM ==========================================

echo ==========================================
echo 智能数据库初始化脚本
echo ==========================================
echo.

REM 查找.env文件
set ENV_FILE=
if exist ".env" (
    set ENV_FILE=.env
) else if exist "release\dist\.env" (
    set ENV_FILE=release\dist\.env
) else if exist "..\release\dist\.env" (
    set ENV_FILE=..\release\dist\.env
)

if "%ENV_FILE%"=="" (
    echo 错误: 找不到.env文件
    echo 请确保在项目根目录或release\dist目录中运行此脚本
    pause
    exit /b 1
)

echo 使用配置文件: %ENV_FILE%
echo.

REM 从.env文件中读取DB_NAME
echo 读取数据库配置...
set DB_NAME=
for /f "tokens=1,2 delims==" %%a in ('type "%ENV_FILE%" ^| findstr /b /c:"DB_NAME"') do (
    set DB_NAME=%%b
)

if "%DB_NAME%"=="" (
    echo 错误: .env文件中未找到DB_NAME配置
    echo 请在.env文件中设置: DB_NAME=your_database_name
    pause
    exit /b 1
)

echo 数据库名: %DB_NAME%
echo.

REM 检查DB_NAME配置是否有效
if "%DB_NAME%"=="your_database_name" (
    echo 警告: DB_NAME仍为默认值
    echo 建议修改为实际的数据库名称
    echo.
)

echo ==========================================
echo 开始数据库初始化
echo ==========================================
echo.
echo 将创建数据库: %DB_NAME%
echo 创建表: file_transfer_log, execution_summary
echo.

REM 询问用户确认
set /p CONFIRM="确认创建数据库 '%DB_NAME%'? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo 用户取消操作
    pause
    exit /b 0
)

echo.
echo 创建数据库...

REM 创建数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS `%DB_NAME%` DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;"

if errorlevel 1 (
    echo.
    echo 错误: 创建数据库失败
    echo 请检查MySQL连接和权限
    pause
    exit /b 1
)

echo 数据库创建成功!
echo.

REM 创建表结构
echo 创建表结构...

REM 创建临时SQL文件
set TEMP_SQL=temp_db_init_%RANDOM%.sql

(
echo USE `%DB_NAME%`;
echo.
echo CREATE TABLE IF NOT EXISTS file_transfer_log ^(
echo     ID INT AUTO_INCREMENT PRIMARY KEY,
echo     SHARE_LINK VARCHAR^(500^) NOT NULL COMMENT '分享链接',
echo     EXTRACTION_CODE VARCHAR^(20^) NOT NULL COMMENT '提取码',
echo     FOLDER_NAME VARCHAR^(255^) NOT NULL COMMENT '目录名称',
echo     FILE_NAME VARCHAR^(255^) NOT NULL COMMENT '文件名',
echo     FILE_PATH VARCHAR^(500^) COMMENT '文件路径',
echo     TRANSFER_STATUS ENUM^('pending', 'downloading', 'uploading', 'success', 'failed', 'skipped'^)
echo         DEFAULT 'pending' COMMENT '传输状态',
echo     ERROR_MESSAGE TEXT COMMENT '错误信息',
echo     START_TIME DATETIME COMMENT '开始时间',
echo     DOWNLOAD_TIME DATETIME COMMENT '下载完成时间',
echo     UPLOAD_TIME DATETIME COMMENT '上传完成时间',
echo     FILE_SIZE BIGINT COMMENT '文件大小^(字节^)',
echo     CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
echo     UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
echo.
echo     INDEX IDX_SHARE_LINK ^(SHARE_LINK^(255^)^),
echo     INDEX IDX_FOLDER_NAME ^(FOLDER_NAME^),
echo     INDEX IDX_STATUS ^(TRANSFER_STATUS^),
echo     INDEX IDX_CREATED_AT ^(CREATED_AT^)
echo ^) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文件传输记录表';
echo.
echo CREATE TABLE IF NOT EXISTS execution_summary ^(
echo     ID INT AUTO_INCREMENT PRIMARY KEY,
echo     SHARE_LINK VARCHAR^(500^) NOT NULL,
echo     FOLDER_NAME VARCHAR^(255^) NOT NULL,
echo     TOTAL_FILES INT DEFAULT 0 COMMENT '总文件数',
echo     SUCCESS_COUNT INT DEFAULT 0 COMMENT '成功数量',
echo     FAILED_COUNT INT DEFAULT 0 COMMENT '失败数量',
echo     SKIPPED_COUNT INT DEFAULT 0 COMMENT '跳过数量',
echo     START_TIME DATETIME COMMENT '执行开始时间',
echo     END_TIME DATETIME COMMENT '执行结束时间',
echo     TOTAL_SIZE BIGINT COMMENT '总文件大小^(字节^)',
echo     CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
echo.
echo     INDEX IDX_CREATED_AT ^(CREATED_AT^)
echo ^) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='执行摘要表';
) > "%TEMP_SQL%"

REM 执行SQL文件
mysql -u root -p < "%TEMP_SQL%"

if errorlevel 1 (
    echo.
    echo 错误: 创建表失败
    del "%TEMP_SQL%"
    pause
    exit /b 1
)

REM 清理临时文件
del "%TEMP_SQL%"

echo 表创建成功!
echo.

REM 验证表创建
echo 验证表创建...
mysql -u root -p -e "USE `%DB_NAME%`; SHOW TABLES;"

echo.
echo ==========================================
echo 数据库初始化完成!
echo ==========================================
echo.
echo 数据库名: %DB_NAME%
echo 配置文件: %ENV_FILE%
echo.
echo 表结构:
echo   - file_transfer_log (文件传输记录)
echo   - execution_summary (执行摘要)
echo.
echo 现在可以运行程序了:
echo   baidu-download.exe --link="..." --folder="..."
echo.
echo 配置已同步，无需修改.env文件！
echo.

pause