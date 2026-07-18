@echo off
chcp 65001 >nul
echo ========================================
echo  闻铎点名器 - 打包脚本
echo ========================================
echo.

REM 清理旧构建
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo [1/3] 正在生成图标...
python src\make_icon.py
if %errorlevel% neq 0 (
    echo 图标生成失败!
    pause
    exit /b 1
)

echo [2/3] 正在打包 EXE...
python -m PyInstaller --onefile --windowed --name "WenDuoPicker" --icon "assets\app_icon.ico" --add-data "src;src" "main.py"

if %errorlevel% neq 0 (
    echo 打包失败!
    pause
    exit /b 1
)

echo [3/3] 重命名...
if exist "dist\WenDuoPicker.exe" (
    ren "dist\WenDuoPicker.exe" "闻铎点名器.exe"
    echo.
    echo ========================================
    echo  打包成功!
    echo  输出文件: dist\闻铎点名器.exe
    echo ========================================
) else (
    echo 未找到输出文件!
)

echo.
pause