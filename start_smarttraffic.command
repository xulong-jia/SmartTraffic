#!/usr/bin/env bash

set -u

pause_before_exit() {
  echo
  read -r -p "按回车键关闭此窗口..." _
}

fail() {
  echo
  echo "错误：$1"
  pause_before_exit
  exit 1
}

cd "$(dirname "$0")" || fail "无法进入 SmartTraffic 项目目录。"

echo "SmartTraffic 一键启动"
echo "项目目录：$(pwd)"
echo

if ! command -v docker >/dev/null 2>&1; then
  fail "未找到 Docker。请先安装 Docker Desktop：https://www.docker.com/products/docker-desktop/"
fi

if ! docker info >/dev/null 2>&1; then
  fail "Docker Desktop 没有启动。请打开 Docker Desktop，等待启动完成后重试。"
fi

if ! docker compose version >/dev/null 2>&1; then
  fail "当前 Docker 不支持 docker compose。请更新 Docker Desktop 后重试。"
fi

if [ ! -f ".env" ]; then
  [ -f ".env.example" ] || fail "找不到 .env.example，无法自动创建 .env。"
  cp ".env.example" ".env" || fail "无法复制 .env.example 到 .env。"
  echo "已自动创建 .env。"
fi

mkdir -p local_videos local_models results evals/results samples || fail "无法创建本地运行目录。"

echo
echo "访问地址："
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo "Health:   http://localhost:8000/health"
echo
echo "正在启动 SmartTraffic。第一次构建可能较慢，请保持 Docker Desktop 运行。"
echo "如需停止，可按 Ctrl+C，或双击 stop_smarttraffic.command。"
echo

docker compose up --build
status=$?

echo
if [ "$status" -ne 0 ]; then
  echo "SmartTraffic 启动失败，退出码：$status"
  echo "请确认 Docker Desktop 已启动，端口 5173 / 8000 未被占用，网络可访问 Docker Hub。"
else
  echo "SmartTraffic 已停止。"
fi

pause_before_exit
exit "$status"
