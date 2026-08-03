@echo off
echo ============================================
echo Rebuilding baidu-download.exe with Playwright support
echo ============================================

echo.
echo [1/3] Cleaning previous build...
rmdir /s /q build release\dist 2>nul

echo [2/3] Building new executable...
pyinstaller baidu_download.spec --clean

echo [3/3] Checking result...
if exist release\dist\baidu-download.exe (
    echo.
    echo ============================================
    echo [SUCCESS] Build completed!
    echo ============================================
    echo Output: release\dist\baidu-download.exe
    echo.
    echo First run will auto-install Playwright browsers:
    echo   baidu-download.exe --wxchat
    echo.
) else (
    echo.
    echo [FAIL] Build failed - executable not found
    echo.
)

pause