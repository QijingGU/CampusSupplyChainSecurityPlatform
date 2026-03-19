@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  校园物资供应链 - 后端启动
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查 8166 端口是否被占用
netstat -ano | findstr ":8166" >nul 2>&1
if not errorlevel 1 (
    echo [警告] 端口 8166 已被占用，请先关闭占用进程
    echo 可执行: netstat -ano ^| findstr 8166 查看进程 PID
    pause
    exit /b 1
)

echo [1/2] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [2/2] 启动后端 (http://127.0.0.1:8166)...
echo 按 Ctrl+C 停止
echo.
uvicorn app.main:app --host 127.0.0.1 --port 8166

pause
