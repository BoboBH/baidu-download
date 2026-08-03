@echo off
echo ============================================
echo Building clean baidu-download package v1.4.3
echo ============================================

echo.
echo [1/3] Cleaning previous build...
rmdir /s /q build dist 2>nul
rmdir /s /q release\dist 2>nul

echo [2/3] Building new executable...
pyinstaller baidu_download.spec --clean

echo [3/3] Preparing release package...
mkdir release\dist
copy dist\baidu-download.exe release\dist\
copy .env release\dist\
copy baidu-cookies.txt release\dist\
copy "D:\tools\BaiduPCS-Go-v4.0.1-windows-x64\BaiduPCS-Go.exe" release\dist\
xcopy /E /I middle release\dist\middle
xcopy /E /I database release\dist\database

echo [4/4] Creating clean package...
cd release\dist
powershell -Command "Compress-Archive -Path '.env', '.env.example', 'baidu-download.exe', 'BaiduPCS-Go.exe', 'baidu-cookies.txt', 'database', 'middle' -DestinationPath '../../baidu-download-v1.4.3.zip' -Force"
cd ..\..

if exist baidu-download-v1.4.3.zip (
    echo.
    echo ============================================
    echo [SUCCESS] Build completed!
    echo ============================================
    echo Output: baidu-download-v1.4.3.zip
    echo Version: 1.4.3
    echo.
    echo Clean version naming - no feature descriptions
    echo.
) else (
    echo.
    echo [FAIL] Build failed - package not found
    echo.
)

pause