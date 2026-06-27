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

echo "正在停止 SmartTraffic..."
echo

if ! command -v docker >/dev/null 2>&1; then
  fail "未找到 Docker。请先安装 Docker Desktop。"
fi

if ! docker compose version >/dev/null 2>&1; then
  fail "当前 Docker 不支持 docker compose。请更新 Docker Desktop 后重试。"
fi

if ! docker info >/dev/null 2>&1; then
  fail "Docker Desktop 可能没有启动。请打开 Docker Desktop 后重试。"
fi

docker compose down
status=$?

echo
if [ "$status" -ne 0 ]; then
  echo "停止失败，退出码：$status"
  echo "请确认 Docker Desktop 正在运行后重试。"
else
  echo "已停止 SmartTraffic。"
  echo "本地数据仍保存在 ignored local directories 中，例如 local_videos、local_models、results、evals/results。"
fi

pause_before_exit
exit "$status"
