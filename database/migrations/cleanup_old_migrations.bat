@echo off
REM Database Migration Cleanup Script for Windows
REM 用途：清理旧的迁移文件，保持目录整洁
REM 使用：cleanup_old_migrations.bat

setlocal enabledelayedexpansion

echo ========================================================================
echo 数据库迁移脚本清理工具
echo ========================================================================

REM 创建归档目录（如果不存在）
if not exist "archive" (
    echo 创建归档目录...
    mkdir archive
    echo [OK] 归档目录创建完成
)

echo.
echo 开始归档旧迁移文件...

REM 定义要移动的文件
set FILES_TO_ARCHIVE=migrate_add_source_field.sql migrate_allow_null_folder_name.sql add_retry_count.sql migrate_rename_wxchat_tables.sql

REM 移动文件到归档目录
for %%f in (%FILES_TO_ARCHIVE%) do (
    if exist "%%f" (
        echo 归档: %%f

        REM 如果文件已存在于归档目录，添加时间戳
        if exist "archive\%%f" (
            set timestamp=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
            set timestamp=!timestamp: =0!
            move "%%f" "archive\%%f_!timestamp!.old" >nul
            echo [OK] 已归档为: archive\%%f_!timestamp!.old
        ) else (
            move "%%f" "archive\%%f" >nul
            echo [OK] 已归档为: archive\%%f
        )
    ) else (
        echo 跳过: %%f (文件不存在)
    )
)

echo.
echo 清理完成状态检查
echo 当前迁移目录状态:
dir *.sql 2>nul | find ".sql"
if errorlevel 1 (
    echo [OK] 主目录已清理完成
)

echo.
echo 归档目录状态:
dir archive\ /b

echo.
echo ========================================================================
echo 迁移脚本清理完成！
echo 注意：旧的迁移文件已移至 archive\ 目录
echo 请使用新的版本化迁移脚本：000*.sql, 001*.sql, 002*.sql, 003*.sql
echo ========================================================================
pause