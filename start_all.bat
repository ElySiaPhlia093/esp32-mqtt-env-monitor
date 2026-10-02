@echo off
title 车间环境智能监测系统 - 一键启动
setlocal

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

echo ============================================================
echo   车间环境智能监测与控制系统  一键启动
echo ============================================================

REM ---------- 环境检查 ----------
if not exist "%BACKEND%\venv\Scripts\python.exe" (
    echo [错误] 后端虚拟环境不存在: %BACKEND%\venv
    echo        请先执行: cd backend ^&^& python -m venv venv ^&^& venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "%FRONTEND%\node_modules" (
    echo [提示] 前端依赖未安装, 正在执行 npm install ...
    pushd "%FRONTEND%"
    call npm install
    popd
)

REM ---------- 启动后端 ----------
echo [1/2] 启动后端 FastAPI  -^>  http://localhost:8000/docs
start "车间系统-后端(8000)" /D "%BACKEND%" cmd /k "venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

REM ---------- 启动前端 ----------
echo [2/2] 启动前端 Vite    -^>  http://localhost:5173
start "车间系统-前端(5173)" /D "%FRONTEND%" cmd /k "npm run dev"

echo.
echo 等待服务就绪 ...
timeout /t 10 /nobreak >nul

echo 打开浏览器 ...
start "" http://localhost:5173

echo.
echo ------------------------------------------------------------
echo  后端接口文档 : http://localhost:8000/docs
echo  前端监测看板 : http://localhost:5173
echo  停止服务     : 关闭弹出的两个命令行窗口
echo ------------------------------------------------------------
echo.
pause
endlocal
