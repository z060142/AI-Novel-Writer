@echo off
chcp 65001 >nul
echo ==========================================
echo   階層式LLM小說創作工具 v3.0 安裝程式
echo ==========================================
echo.

echo [1/3] 檢查Python版本...
python --version 2>nul
if errorlevel 1 (
    echo ❌ 未找到Python，請先安裝Python 3.11+
    echo    下載地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ 發現Python %PYTHON_VERSION%

echo.
echo [2/3] 安裝相依套件...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 套件安裝失敗
    pause
    exit /b 1
)
echo ✅ 套件安裝完成

echo.
echo [3/3] 啟動程式...
echo ✅ 安裝完成！正在啟動小說創作工具...
echo.
python novel_writer.py

pause