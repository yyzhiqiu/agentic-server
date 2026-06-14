#!/usr/bin/env bash

set -Eeuo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$DEPLOY_DIR")"
BACKEND_DIR="$ROOT_DIR/backend"
WEB_DIR="$ROOT_DIR/web"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
BACKEND_WORKERS="${BACKEND_WORKERS:-1}"
VENV_DIR="${VENV_DIR:-$BACKEND_DIR/.venv}"
PYTHON="${PYTHON:-$VENV_DIR/bin/python}"
RUNTIME_DIR="${RUNTIME_DIR:-$BACKEND_DIR/run}"
LOG_DIR="${LOG_DIR:-$BACKEND_DIR/logs}"
PID_FILE="$RUNTIME_DIR/agentic-server.pid"
LOG_FILE="$LOG_DIR/agentic-server.log"
HEALTH_URL="http://$BACKEND_HOST:$BACKEND_PORT/health"
ACTION="${1:-deploy}"

log() {
  printf '[发布] %s\n' "$1"
}

fail() {
  printf '[发布失败] %s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "未找到命令：$1"
}

read_pid() {
  if [[ -f "$PID_FILE" ]]; then
    tr -d '[:space:]' < "$PID_FILE"
  fi
}

is_running() {
  local pid
  pid="$(read_pid)"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

prepare_runtime_dirs() {
  mkdir -p "$RUNTIME_DIR" "$LOG_DIR"
}

check_backend_environment() {
  require_command "curl"

  [[ -f "$BACKEND_DIR/.env" ]] || fail \
    "缺少 backend/.env，请先根据 backend/.env.example 创建生产配置"
  [[ -x "$PYTHON" ]] || fail \
    "未找到后端虚拟环境，请先执行 bash deploy/deploy.sh deploy"
}

check_deploy_environment() {
  require_command "pnpm"
  require_command "python3"
  require_command "curl"

  [[ -f "$BACKEND_DIR/.env" ]] || fail \
    "缺少 backend/.env，请先根据 backend/.env.example 创建生产配置"
}

build_web() {
  log "安装前端依赖"
  (
    cd "$WEB_DIR"
    pnpm install --frozen-lockfile
  )

  log "构建前端静态文件"
  (
    cd "$WEB_DIR"
    VITE_API_BASE_URL="" pnpm build
  )
}

prepare_backend() {
  if [[ ! -x "$PYTHON" ]]; then
    log "创建 Python 虚拟环境：$VENV_DIR"
    python3 -m venv "$VENV_DIR"
  fi

  log "安装后端依赖"
  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install -r "$BACKEND_DIR/requirements.txt"

  log "执行数据库迁移"
  (
    cd "$BACKEND_DIR"
    "$PYTHON" -m alembic upgrade head
  )
}

stop_backend() {
  local pid
  pid="$(read_pid)"

  if [[ -z "$pid" ]]; then
    log "未找到后端 PID 文件，无需停止"
    return
  fi

  if ! kill -0 "$pid" 2>/dev/null; then
    log "清理已失效的 PID 文件"
    rm -f "$PID_FILE"
    return
  fi

  log "停止后端进程：$pid"
  kill "$pid" 2>/dev/null || true

  for _ in {1..20}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PID_FILE"
      log "后端进程已停止"
      return
    fi
    sleep 1
  done

  log "后端进程未在超时时间内退出，执行强制停止"
  kill -9 "$pid"
  rm -f "$PID_FILE"
}

start_backend() {
  prepare_runtime_dirs

  if is_running; then
    fail "后端已在运行，PID：$(read_pid)"
  fi

  rm -f "$PID_FILE"
  log "启动后端：http://$BACKEND_HOST:$BACKEND_PORT"
  (
    cd "$BACKEND_DIR"
    nohup env APP_ENV=production DEBUG=false \
      "$PYTHON" -m uvicorn app.main:app \
      --host "$BACKEND_HOST" \
      --port "$BACKEND_PORT" \
      --workers "$BACKEND_WORKERS" \
      >> "$LOG_FILE" 2>&1 &
    echo "$!" > "$PID_FILE"
  )

  for _ in {1..30}; do
    if curl --silent --show-error --fail "$HEALTH_URL" >/dev/null 2>&1; then
      log "后端健康检查通过"
      return
    fi

    if ! is_running; then
      rm -f "$PID_FILE"
      tail -n 100 "$LOG_FILE" >&2 || true
      fail "后端进程启动后异常退出"
    fi

    sleep 1
  done

  stop_backend
  tail -n 100 "$LOG_FILE" >&2 || true
  fail "后端健康检查超时：$HEALTH_URL"
}

show_status() {
  if is_running; then
    log "后端正在运行，PID：$(read_pid)"
    log "健康检查：$HEALTH_URL"
    log "日志文件：$LOG_FILE"
    return
  fi

  log "后端当前未运行"
  [[ ! -f "$PID_FILE" ]] || rm -f "$PID_FILE"
  return 1
}

deploy() {
  check_deploy_environment
  prepare_runtime_dirs
  build_web
  prepare_backend
  stop_backend
  start_backend

  log "发布完成"
  log "前端目录：$WEB_DIR/dist"
  log "后端日志：$LOG_FILE"
  log "请确认 Nginx 已加载 deploy/nginx/macmini.conf"
}

case "$ACTION" in
  deploy)
    deploy
    ;;
  start)
    check_backend_environment
    start_backend
    ;;
  stop)
    stop_backend
    ;;
  restart)
    check_backend_environment
    stop_backend
    start_backend
    ;;
  status)
    show_status
    ;;
  *)
    fail "未知操作：$ACTION，可用操作为 deploy、start、stop、restart、status"
    ;;
esac
