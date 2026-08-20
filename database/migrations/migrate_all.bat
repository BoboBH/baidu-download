@echo off
REM Database Migration Script for Windows
REM 用途：执行所有未执行的数据库迁移
REM 使用：migrate_all.bat [database_name] [mysql_user]

setlocal enabledelayedexpansion

REM 配置参数
set DB_NAME=%1
if "%DB_NAME%"=="" set DB_NAME=baidu_download

set MYSQL_USER=%2
if "%MYSQL_USER%"=="" set MYSQL_USER=root

set MIGRATION_DIR=database\migrations
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_FILE=backup_before_migration_%TIMESTAMP%.sql

echo ========================================================================
echo 数据库迁移脚本 - %DB_NAME%
echo ========================================================================

REM 检查数据库连接
echo 检查数据库连接...
mysql -u %MYSQL_USER% -p -e "USE %DB_NAME%;" >nul 2>&1
if errorlevel 1 (
    echo 错误：无法连接到数据库 '%DB_NAME%' 或数据库不存在
    echo 请先创建数据库或检查连接参数
    pause
    exit /b 1
)
echo [OK] 数据库连接正常

REM 创建备份
echo 创建数据库备份到: %BACKUP_FILE%
mysqldump -u %MYSQL_USER% -p %DB_NAME% > %BACKUP_FILE%
if errorlevel 1 (
    echo 错误：备份失败
    pause
    exit /b 1
)
echo [OK] 备份完成

REM 执行迁移文件
echo.
echo 执行迁移文件...

REM 000 初始架构
echo [1/4] 执行: 000_init_schema.sql
if exist "%MIGRATION_DIR%\000_init_schema.sql" (
    mysql -u %MYSQL_USER% -p %DB_NAME% < "%MIGRATION_DIR%\000_init_schema.sql"
    if errorlevel 1 (
        echo 错误：000_init_schema.sql 执行失败
        echo 您可以尝试从备份恢复: mysql -u %MYSQL_USER% -p %DB_NAME% < %BACKUP_FILE%
        pause
        exit /b 1
    )
    echo [OK] 000_init_schema.sql 执行完成
) else (
    echo 警告：000_init_schema.sql 文件不存在，跳过
)

REM 001 添加 source 字段
echo [2/4] 执行: 001_add_source_field.sql
mysql -u %MYSQL_USER% -p %DB_NAME% -e "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='%DB_NAME%' AND TABLE_NAME='message_process_log' AND COLUMN_NAME='source';" 2>nul | findstr /C:"source" >nul
if errorlevel 1 (
    if exist "%MIGRATION_DIR%\001_add_source_field.sql" (
        mysql -u %MYSQL_USER% -p %DB_NAME% < "%MIGRATION_DIR%\001_add_source_field.sql"
        if errorlevel 1 (
            echo 错误：001_add_source_field.sql 执行失败
            pause
            exit /b 1
        )
        echo [OK] 001_add_source_field.sql 执行完成
    ) else (
        echo 警告：001_add_source_field.sql 文件不存在，跳过
    )
) else (
    echo [OK] 001_add_source_field.sql 已执行，跳过
)

REM 002 允许 folder_name 为 NULL
echo [3/4] 执行: 002_allow_null_folder_name.sql
mysql -u %MYSQL_USER% -p %DB_NAME% -e "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='%DB_NAME%' AND TABLE_NAME='message_process_log' AND COLUMN_NAME='folder_name';" 2>nul | findstr /C:"YES" >nul
if errorlevel 1 (
    if exist "%MIGRATION_DIR%\002_allow_null_folder_name.sql" (
        mysql -u %MYSQL_USER% -p %DB_NAME% < "%MIGRATION_DIR%\002_allow_null_folder_name.sql"
        if errorlevel 1 (
            echo 错误：002_allow_null_folder_name.sql 执行失败
            pause
            exit /b 1
        )
        echo [OK] 002_allow_null_folder_name.sql 执行完成
    ) else (
        echo 警告：002_allow_null_folder_name.sql 文件不存在，跳过
    )
) else (
    echo [OK] 002_allow_null_folder_name.sql 已执行，跳过
)

REM 003 添加 retry_count 字段
echo [4/4] 执行: 003_add_retry_count.sql
mysql -u %MYSQL_USER% -p %DB_NAME% -e "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='%DB_NAME%' AND TABLE_NAME='message_process_log' AND COLUMN_NAME='retry_count';" 2>nul | findstr /C:"retry_count" >nul
if errorlevel 1 (
    if exist "%MIGRATION_DIR%\003_add_retry_count.sql" (
        mysql -u %MYSQL_USER% -p %DB_NAME% < "%MIGRATION_DIR%\003_add_retry_count.sql"
        if errorlevel 1 (
            echo 错误：003_add_retry_count.sql 执行失败
            pause
            exit /b 1
        )
        echo [OK] 003_add_retry_count.sql 执行完成
    ) else (
        echo 警告：003_add_retry_count.sql 文件不存在，跳过
    )
) else (
    echo [OK] 003_add_retry_count.sql 已执行，跳过
)

REM 验证最终状态
echo.
echo 验证数据库结构...
mysql -u %MYSQL_USER% -p %DB_NAME% -e "SELECT TABLE_NAME, TABLE_COMMENT FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='%DB_NAME%' ORDER BY TABLE_NAME;"

echo.
echo message_process_log 表结构:
mysql -u %MYSQL_USER% -p %DB_NAME% -e "DESCRIBE message_process_log;"

echo ========================================================================
echo 所有迁移执行完成！
echo 备份文件: %BACKUP_FILE%
echo ========================================================================
pause