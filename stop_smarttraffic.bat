@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo 正在停止 SmartTraffic...
echo.

docker compose version >nul 2>&1
if errorlevel 1 (
  echo 错误：当前 Docker 不支持 docker compose。请确认 Docker Desktop 已安装并启动。
  pause
  exit /b 1
)

docker compose down
set "STATUS=%ERRORLEVEL%"

echo.
if not "%STATUS%"=="0" (
  echo 停止失败，退出码：%STATUS%
  echo 请确认 Docker Desktop 正在运行后重试。
  pause
  exit /b %STATUS%
)

echo 已停止 SmartTraffic。
echo 本地数据仍保存在 ignored local directories 中，例如 local_videos、local_models、results、evals\results。
pause
exit /b 0
