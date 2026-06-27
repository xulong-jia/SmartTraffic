@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo SmartTraffic 一键启动
echo 项目目录：%CD%
echo.

docker --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo 错误：未找到 Docker。请先安装 Docker Desktop：
  echo https://www.docker.com/products/docker-desktop/
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo.
  echo 错误：Docker Desktop 没有启动。请打开 Docker Desktop，等待启动完成后重试。
  pause
  exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
  echo.
  echo 错误：当前 Docker 不支持 docker compose。请更新 Docker Desktop 后重试。
  pause
  exit /b 1
)

if not exist ".env" (
  if not exist ".env.example" (
    echo.
    echo 错误：找不到 .env.example，无法自动创建 .env。
    pause
    exit /b 1
  )
  copy ".env.example" ".env" >nul
  if errorlevel 1 (
    echo.
    echo 错误：无法复制 .env.example 到 .env。
    pause
    exit /b 1
  )
  echo 已自动创建 .env。
)

if not exist "local_videos" mkdir "local_videos"
if not exist "local_models" mkdir "local_models"
if not exist "results" mkdir "results"
if not exist "evals\results" mkdir "evals\results"
if not exist "samples" mkdir "samples"

echo.
echo 访问地址：
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000
echo Health:   http://localhost:8000/health
echo.
echo 正在启动 SmartTraffic。第一次构建可能较慢，请保持 Docker Desktop 运行。
echo 如需停止，可按 Ctrl+C，或双击 stop_smarttraffic.bat。
echo.

docker compose up --build
set "STATUS=%ERRORLEVEL%"

echo.
if not "%STATUS%"=="0" (
  echo SmartTraffic 启动失败，退出码：%STATUS%
  echo 请确认 Docker Desktop 已启动，端口 5173 / 8000 未被占用，网络可访问 Docker Hub。
  pause
  exit /b %STATUS%
)

echo SmartTraffic 已停止。
pause
exit /b 0
