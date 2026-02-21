#!/bin/bash

# set -ex

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_DIR=$(cd ${SCRIPT_DIR}/.. && pwd)
cd "${SCRIPT_DIR}"

upload_file() {
  source_file="$1"
  target_path="$2"

  if [ -f "${source_file}" ]; then
    MAX_RETRY=5
    for ((i = 1; i <= MAX_RETRY; i++)); do
      scp -q "${source_file}" host-154:${target_path} && {
        echo "文件(${source_file})传输成功。"
        break
      }
      [ $i -eq $MAX_RETRY ] && break
      sleep 10
    done
  else
    echo "文件(${source_file})不存在，跳过传输。"
  fi
}

update_api() {
  cd "${PROJECT_DIR}/backend" && git pull
  cd "${PROJECT_DIR}/spider" && git pull
  bash "/home/DevTools/linux-develop/docker-app/tvbox/docker-migu.sh" run
  sleep 10
}

update_m3u() {
  curl -X 'POST' \
    'http://192.168.3.144:8001/tv/update/migu' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{
  "output": "/tmp/migu3721.txt",
  "epg": {
    "file": "/tmp/migu-e.xml",
    "url": "https://ak3721.top/tv/epg/migu-e.xml",
    "source": "&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}",
	"show_logo": "True"
  }
}' >/dev/null 2>&1

  target_file='/tmp/migu3721.m3u'
  MAX_TIMEOUT=300
  CHECK_INTERVAL=2
  COUNTER=0
  while true; do
    if [ -f "${target_file}" ]; then
      upload_file "${target_file}" "/home/app/tvbox/spider/dist/json/"
      break
    fi
    if [ ${COUNTER} -ge ${MAX_TIMEOUT} ]; then
      break
    fi
    COUNTER=$((COUNTER + CHECK_INTERVAL))
    sleep ${CHECK_INTERVAL}
  done
  upload_file "/tmp/migu-e.xml" "/home/app/tvbox/spider/dist/epg/"
}

case "$1" in
  all)
    echo "update all"
    update_api
    update_m3u
    ;;
  api)
    echo "update api"
    update_api
    ;;
  m3u)
    echo "update m3u"
    update_m3u
    ;;
  epg)
    echo "upload file"
    upload_file "$2/epg"/*.xml "/home/app/tvbox/spider/dist/epg/"
    upload_file "$2/epg"/result.m3u  "/home/app/tvbox/spider/dist/json/"
    upload_file "$2/epg"/result.txt  "/home/app/tvbox/spider/dist/json/"
    ;;
  *)
    echo "usage: $0 {all|api|m3u|epg}"
    exit 1
    ;;
esac
