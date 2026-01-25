#!/bin/bash

SCRIPT_DIR=$(
  cd "$(dirname "$0")" || exit 1
  pwd
)
cd "$SCRIPT_DIR" || exit 1

curl -X 'POST' \
  'http://192.168.3.144:3000/tv/update/migu' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "output": "/tmp/migu3721.txt",
  "epg": {
    "file": "https://gh-proxy.org/github.com/develop202/migu_video/blob/main/playback.xml",
    "source": "&playbackbegin=${(b)yyyyMMddHHmmss}&playbackend=${(e)yyyyMMddHHmmss}"
  }
}' >/dev/null 2>&1

TARGET_FILE='/tmp/migu3721.m3u'
MAX_TIMEOUT=300
CHECK_INTERVAL=2
COUNTER=0
while true; do
  if [ -f "${TARGET_FILE}" ]; then
    scp -q ${TARGET_FILE} host-154:/home/app/tvbox/spider/dist/json/
    echo "文件传输成功，退出检测循环。"
    break
  fi
  if [ ${COUNTER} -ge ${MAX_TIMEOUT} ]; then
    break
  fi
  COUNTER=$((COUNTER + CHECK_INTERVAL))
  sleep ${CHECK_INTERVAL}
done
