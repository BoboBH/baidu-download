@echo off
REM 百度网盘PDF文件自动传输系统 - 数据库初始化脚本 (Windows)
REM 使用方法: init_db.bat [数据库名]
REM 示例: init_db.bat my_project

setlocal

if "%~1"=="" (
    set DB_NAME=baidu_download
) else (
    set DB_NAME=%~1
)

echo ==========================================
echo 数据库初始化脚本
echo ==========================================
echo 数据库名: %DB_NAME%

echo.
echo 创建数据库: %DB_NAME%

mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS `%DB_NAME%` DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;"

if errorlevel 1 (
    echo 错误: 创建数据库失败
    pause
    exit /b 1
)

echo.
echo 创建表结构...

mysql -u root -p -D %DB_NAME% < middle\db_init.sql

if errorlevel 1 (
    echo 错误: 创建表失败
    pause
    exit /b 1
)

echo.
echo 验证表创建...
mysql -u root -p -e "USE `%DB_NAME%`; SHOW TABLES;"

echo.
echo ==========================================
echo 数据库初始化完成!
echo 数据库名: %DB_NAME%
echo ==========================================
echo.
echo 重要: 请更新 release\dist\.env 文件中的 DB_NAME=%DB_NAME%
echo.

pause
