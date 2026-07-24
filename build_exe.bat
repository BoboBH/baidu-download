@echo off
REM ==============================================================================
REM 百度网盘PDF文件自动传输系统 - Windows可执行文件构建脚本
REM
REM 功能:
REM   1. 检查PyInstaller安装状态
REM   2. 清理之前的构建文件
REM   3. 使用PyInstaller构建可执行文件
REM   4. 复制必要的配置文件到构建目录
REM   5. 创建部署包结构
REM   6. 提供构建结果反馈
REM
REM 使用方法:
REM   build_exe.bat              # 标准构建
REM   build_exe.bat clean        # 强制清理构建
REM   build_exe.bat debug        # 调试模式 (显示详细信息)
REM
REM 作者: baidu-download team
REM 版本: 1.1.5
REM ==============================================================================

setlocal enabledelayedexpansion

REM 配置变量
set "PROJECT_NAME=baidu-download"
set "SPEC_FILE=baidu_download.spec"
set "BUILD_DIR=build"
set "DIST_DIR=dist"
set "PYTHON_EXE=python"

REM 颜色设置 (Windows 10+)
set "INFO=[92m"    # 绿色
set "WARN=[93m"    # 黄色
set "ERROR=[91m"   # 红色
set "RESET=[0m"    # 重置

REM ============================================================================
REM 函数定义
REM ============================================================================

:print_info
echo %INFO%[INFO]%RESET% %~1
goto :eof

:print_warn
echo %WARN%[WARN]%RESET% %~1
goto :eof

:print_error
echo %ERROR%[ERROR]%RESET% %~1
goto :eof

:print_section
echo.
echo %INFO%========================================%RESET%
echo %INFO%  %~1%RESET%
echo %INFO%========================================%RESET%
echo.

REM ============================================================================
REM 主程序开始
REM ============================================================================

call :print_section "百度网盘PDF文件自动传输系统 - Windows构建脚本"

REM 检查命令行参数
set "CLEAN_BUILD=0"
set "DEBUG_MODE=0"

if "%~1"=="clean" set "CLEAN_BUILD=1"
if "%~1"=="debug" set "DEBUG_MODE=1"
if "%~2"=="debug" set "DEBUG_MODE=1"

REM ============================================================================
REM Step 1: 环境检查
REM ============================================================================

call :print_section "Step 1: 环境检查"

REM 检查Python是否可用
%PYTHON_EXE% --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Python未找到或无法执行！"
    call :print_error "请确保Python已安装并添加到PATH环境变量中"
    exit /b 1
)
call :print_info "Python版本检查通过"

REM 检查PyInstaller是否安装
%PYTHON_EXE% -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    call :print_warn "PyInstaller未安装！"
    call :print_info "正在安装PyInstaller..."
    %PYTHON_EXE% -m pip install pyinstaller
    if errorlevel 1 (
        call :print_error "PyInstaller安装失败！"
        call :print_error "请手动运行: pip install pyinstaller"
        exit /b 1
    )
    call :print_info "PyInstaller安装成功"
) else (
    call :print_info "PyInstaller已安装"
)

REM 检查项目文件是否存在
if not exist "%SPEC_FILE%" (
    call :print_error "找不到规范文件: %SPEC_FILE%"
    exit /b 1
)

if not exist "main.py" (
    call :print_error "找不到主程序文件: main.py"
    exit /b 1
)

if not exist "BaiduPCS-Go.exe" (
    call :print_warn "警告: 找不到BaiduPCS-Go.exe"
    call :print_warn "可执行文件将无法正常工作！"
)

call :print_info "环境检查完成"

REM ============================================================================
REM Step 2: 清理构建目录
REM ============================================================================

call :print_section "Step 2: 清理构建目录"

if %CLEAN_BUILD%==1 (
    call :print_info "强制清理模式: 删除所有构建文件"
    if exist "%BUILD_DIR%" (
        rmdir /s /q "%BUILD_DIR%" 2>nul
        call :print_info "已删除构建目录: %BUILD_DIR%"
    )
    if exist "%DIST_DIR%" (
        rmdir /s /q "%DIST_DIR%" 2>nul
        call :print_info "已删除分发目录: %DIST_DIR%"
    )
) else (
    call :print_info "标准清理: 保留部分构建文件"
    REM 仅删除PyInstaller生成的特定目录
    if exist "%BUILD_DIR%\%PROJECT_NAME%" (
        rmdir /s /q "%BUILD_DIR%\%PROJECT_NAME%" 2>nul
        call :print_info "已清理: %BUILD_DIR%\%PROJECT_NAME%"
    )
)

REM ============================================================================
REM Step 3: 构建可执行文件
REM ============================================================================

call :print_section "Step 3: 构建可执行文件"

set "PYINSTALLER_CMD=pyinstaller"
if %DEBUG_MODE%==1 (
    set "PYINSTALLER_CMD=pyinstaller --debug=all --log-level=DEBUG"
    call :print_info "调试模式已启用"
)

call :print_info "开始构建..."
call :print_info "这可能需要几分钟时间，请耐心等待..."

%PYTHON_EXE% -m %PYINSTALLER_CMD% %SPEC_FILE%
if errorlevel 1 (
    call :print_error "PyInstaller构建失败！"
    call :print_error "请检查上面的错误信息"
    exit /b 1
)

call :print_info "PyInstaller构建成功"

REM ============================================================================
REM Step 4: 验证构建结果
REM ============================================================================

call :print_section "Step 4: 验证构建结果"

if not exist "%DIST_DIR%\%PROJECT_NAME%.exe" (
    call :print_error "构建失败: 找不到生成的可执行文件"
    call :print_error "预期位置: %DIST_DIR%\%PROJECT_NAME%.exe"
    exit /b 1
)

call :print_info "可执行文件已创建: %DIST_DIR%\%PROJECT_NAME%.exe"

REM 获取文件大小
for %%F in ("%DIST_DIR%\%PROJECT_NAME%.exe") do set "FILE_SIZE=%%~zF"
set /a "FILE_SIZE_MB=%FILE_SIZE% / 1048576"
call :print_info "文件大小: 约 %FILE_SIZE_MB% MB"

REM ============================================================================
REM Step 5: 部署后处理
REM ============================================================================

call :print_section "Step 5: 部署后处理"

REM 复制配置文件模板到构建目录 (简化部署)
if exist ".env.example" (
    copy ".env.example" "%DIST_DIR%\.env.example" >nul
    call :print_info "已复制: .env.example 到构建目录"
)

REM PyInstaller会自动包含所有必要文件，无需手动创建复杂目录结构

REM ============================================================================
REM Step 6: 构建完成总结
REM ============================================================================

call :print_section "Step 6: 构建完成总结"

call :print_info "构建成功完成！"
echo.
echo 部署文件位置:
echo   可执行文件: %DIST_DIR%\%PROJECT_NAME%.exe
echo   部署目录:   %DEPLOY_DIR%
echo.
echo 下一步操作:
echo 1. 将部署目录复制到目标服务器
echo 2. 配置.env文件
echo 3. 测试可执行文件
echo 4. 设置Windows任务计划程序 (如需要)
echo.

call :print_info "构建完成！可执行文件位于: %DIST_DIR%\%PROJECT_NAME%.exe"
call :print_info "配置说明请参考: BUILD_README.md"
call :print_info "构建脚本执行完成"
goto :eof

REM ============================================================================
REM 错误处理
REM ============================================================================

:cleanup
call :print_error "构建过程中出现错误"
call :print_error "请检查环境配置和依赖项"
exit /b 1