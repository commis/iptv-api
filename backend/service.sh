#!/bin/bash

#set -ex

SCRIPT_DIR=$(
  cd "$(dirname "$0")" || exit 1
  pwd
)
cd "$SCRIPT_DIR" || exit 1

ENV_FILE="${SCRIPT_DIR}/../.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: $ENV_FILE not found." >&2
  exit 1
fi
source "${SCRIPT_DIR}/../.env"

PIDFILE="/var/run//tvbox.pid"
COMMAND="gunicorn -c gunicorn.conf.py application:app"

function init_env() {
  if [ -f "$PYENV/bin/activate" ]; then
    source "$PYENV/bin/activate"
  else
    echo "Error: virtual environment not found." >&2
    exit 1
  fi
  export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
}

function is_running() {
  [ -f "$PIDFILE" ] && ps -p "$(cat "$PIDFILE")" >/dev/null 2>&1
}

function get_pid() {
  if [ -f "$PIDFILE" ]; then
    echo "$(cat "$PIDFILE")"
  else
    pgrep -f "$COMMAND"
  fi
}

function start() {
  if is_running; then
    echo "Service is already running."
    return 0
  fi

  $COMMAND >/dev/null 2>&1 &
  echo $! >"$PIDFILE"

  sleep 2
  if is_running; then
    echo "Service started successfully.，PID: $(cat "$PIDFILE")"
  else
    echo "Service failed to start." >&2
    rm -f "$PIDFILE"
    return 1
  fi
}

function stop() {
  PID=$(get_pid)

  if [ -z "$PID" ]; then
    echo "Service is not running."
    [ -f "$PIDFILE" ] && rm -f "$PIDFILE"
    return 0
  fi

  kill -15 "$PID"

  # 等待服务停止
  TIMEOUT=10
  while is_running && [ $TIMEOUT -gt 0 ]; do
    sleep 1
    TIMEOUT=$((TIMEOUT - 1))
  done

  if is_running; then
    kill -9 "$PID"
    sleep 1
  fi

  if ! is_running; then
    echo "Service stopped successfully. PID: $PID"
    [ -f "$PIDFILE" ] && rm -f "$PIDFILE"
  else
    echo "Service failed to stop. Check $LOGFILE" >&2
    return 1
  fi
}

function status() {
  if is_running; then
    PID=$(get_pid)
    echo "Service is running. PID: $PID"

    # 显示内存和CPU使用情况
    echo "Resources:"
    ps -p "$PID" -o %cpu,%mem,cmd
  else
    echo "Service is not running."
  fi
}

init_env
case "$1" in
start)
  start
  ;;

stop)
  stop
  ;;

status)
  status
  ;;

restart)
  stop
  start
  ;;

*)
  echo "usage: $0 {start|stop|status|restart}"
  exit 1
  ;;
esac
