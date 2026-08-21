@echo off
REM 打包脚本 - 将项目打包为exe

echo ====================================
echo 百度网盘PDF传输系统打包脚本
echo ====================================
echo.

REM 检查PyInstaller是否安装
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller未安装，正在安装...
    pip install pyinstaller
)

echo 开始打包主程序...
pyinstaller baidu-download.spec

if errorlevel 1 (
    echo 打包失败！
    pause
    exit /b 1
)

echo.
echo ====================================
echo 打包完成！
echo 可执行文件位置: dist\baidu-download.exe
echo ====================================

REM 复制必要文件到dist目录
copy .env.example dist\
copy middle\db_init.sql dist\
copy README.md dist\README.txt

echo.
echo 发布包已准备完成，位于 dist\ 目录
pause
