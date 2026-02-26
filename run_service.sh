#!/bin/bash

# Memory Card 服务管理脚本

SERVICE_NAME="memory-card"

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RUN_DIR="$PROJECT_DIR/.run"
PID_FILE="$RUN_DIR/${SERVICE_NAME}.pid"
LOG_FILE="$RUN_DIR/${SERVICE_NAME}.log"

APP_MODULE="$PROJECT_DIR/core/app.py"
PORT="${PORT:-5001}"
HOST="${HOST:-127.0.0.1}"

has_cmd() { command -v "$1" >/dev/null 2>&1; }

get_python() {
  # 优先使用项目 venv（如果存在且可执行）
  if [[ -x "$PROJECT_DIR/venv/bin/python" ]]; then
    echo "$PROJECT_DIR/venv/bin/python"
    return
  fi
  if has_cmd python3; then
    echo "python3"
    return
  fi
  echo "python"
}

is_running_pid() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

mac_start() {
  mkdir -p "$RUN_DIR"
  if has_cmd lsof; then
    if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "端口 $PORT 已被占用，无法启动。"
      echo "占用进程："
      lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
      echo ""
      echo "解决方式："
      echo "  - 换端口启动：PORT=5001 $0 start"
      echo "  - 或停止占用该端口的进程"
      exit 1
    fi
  fi
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if is_running_pid "$pid"; then
      echo "服务已在运行（pid=${pid}）"
      echo "日志: $LOG_FILE"
      return 0
    fi
    rm -f "$PID_FILE"
  fi

  local py
  py="$(get_python)"
  if [[ ! -f "$APP_MODULE" ]]; then
    echo "找不到后端入口: $APP_MODULE"
    exit 1
  fi

  echo "在 macOS 上启动 Memory Card（后台运行，PORT=${PORT}）..."
  HOST="$HOST" PORT="$PORT" nohup "$py" "$APP_MODULE" >"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  sleep 0.6

  local pid
  pid="$(cat "$PID_FILE")"
  if is_running_pid "$pid"; then
    echo "启动成功（pid=${pid}）"
    echo "访问: http://${HOST}:${PORT}"
    echo "日志: $LOG_FILE"
  else
    echo "启动失败，请查看日志: $LOG_FILE"
    tail -n 50 "$LOG_FILE" || true
    exit 1
  fi
}

mac_stop() {
  if [[ ! -f "$PID_FILE" ]]; then
    echo "未发现 PID 文件，服务可能未运行。"
    return 0
  fi
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if ! is_running_pid "$pid"; then
    echo "服务未运行（pid=${pid}），清理 PID 文件。"
    rm -f "$PID_FILE"
    return 0
  fi
  echo "停止 Memory Card（pid=${pid}）..."
  kill "$pid" 2>/dev/null || true
  # 等待优雅退出
  for _ in {1..30}; do
    if ! is_running_pid "$pid"; then
      rm -f "$PID_FILE"
      echo "已停止。"
      return 0
    fi
    sleep 0.2
  done
  echo "未能优雅停止，强制 kill -9（pid=${pid}）..."
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "已强制停止。"
}

mac_status() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if is_running_pid "$pid"; then
      echo "running (pid=${pid})"
      echo "日志: $LOG_FILE"
      exit 0
    fi
    echo "not running (stale pidfile pid=${pid})"
    rm -f "$PID_FILE" || true
    exit 3
  fi
  echo "not running"
  exit 3
}

mac_logs() {
  mkdir -p "$RUN_DIR"
  touch "$LOG_FILE"
  tail -n 200 -f "$LOG_FILE"
}

use_systemd=false
if has_cmd systemctl; then
  use_systemd=true
fi
if [[ "${OSTYPE:-}" == "linux-gnu"* ]]; then
  # 在 Linux 上优先使用 systemd（如果存在）
  :
elif [[ "${OSTYPE:-}" == "darwin"* ]]; then
  use_systemd=false
fi

cmd="${1:-}"
if [[ -z "$cmd" ]]; then
  echo "用法: $0 {start|stop|restart|status|enable|disable|logs|install}"
  echo ""
  echo "命令说明:"
  echo "  start   - 启动服务"
  echo "  stop    - 停止服务"
  echo "  restart - 重启服务"
  echo "  status  - 查看服务状态"
  echo "  enable  - 设置开机自启"
  echo "  disable - 禁用开机自启"
  echo "  logs    - 查看实时日志"
  echo "  install - 安装并启动服务"
  exit 1
fi

case "$cmd" in
    start)
        if $use_systemd; then
          echo "启动 Memory Card 服务（systemd）..."
          sudo systemctl start "$SERVICE_NAME"
          sudo systemctl status "$SERVICE_NAME"
        else
          mac_start
        fi
        ;;
    stop)
        if $use_systemd; then
          echo "停止 Memory Card 服务（systemd）..."
          sudo systemctl stop "$SERVICE_NAME"
        else
          mac_stop
        fi
        ;;
    restart)
        if $use_systemd; then
          echo "重启 Memory Card 服务（systemd）..."
          sudo systemctl restart "$SERVICE_NAME"
          sudo systemctl status "$SERVICE_NAME"
        else
          mac_stop
          mac_start
        fi
        ;;
    status)
        if $use_systemd; then
          sudo systemctl status "$SERVICE_NAME"
        else
          mac_status
        fi
        ;;
    enable)
        if $use_systemd; then
          echo "设置 Memory Card 服务开机自启（systemd）..."
          sudo systemctl enable "$SERVICE_NAME"
        else
          echo "macOS 下请使用 launchd（LaunchAgents/LaunchDaemons）。"
          echo "当前脚本已支持 start/stop/status/logs（基于 PID 文件）。"
        fi
        ;;
    disable)
        if $use_systemd; then
          echo "禁用 Memory Card 服务开机自启（systemd）..."
          sudo systemctl disable "$SERVICE_NAME"
        else
          echo "macOS 下请使用 launchd（LaunchAgents/LaunchDaemons）。"
        fi
        ;;
    logs)
        if $use_systemd; then
          echo "查看 Memory Card 服务日志（systemd）..."
          sudo journalctl -u "$SERVICE_NAME" -f
        else
          echo "查看 Memory Card 日志（macOS）..."
          mac_logs
        fi
        ;;
    install)
        if $use_systemd; then
          echo "安装并启动 Memory Card 服务（systemd）..."
          sudo systemctl daemon-reload
          sudo systemctl enable "$SERVICE_NAME"
          sudo systemctl start "$SERVICE_NAME"
          sudo systemctl status "$SERVICE_NAME"
        else
          echo "macOS 下 install 不做 systemd 安装。"
          echo "你可以先用: ./run_service.sh start"
          echo "如需开机自启，可用 launchd（可再告诉我我帮你生成 plist）。"
        fi
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|enable|disable|logs|install}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动服务"
        echo "  stop    - 停止服务"
        echo "  restart - 重启服务"
        echo "  status  - 查看服务状态"
        echo "  enable  - 设置开机自启"
        echo "  disable - 禁用开机自启"
        echo "  logs    - 查看实时日志"
        echo "  install - 安装并启动服务"
        exit 1
        ;;
esac 