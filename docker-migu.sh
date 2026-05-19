#!/bin/bash -e

TAG=latest
CODE_DIR=/home/app/tvbox

scriptpath=$(
  cd "$(dirname "$0")" || exit 1
  pwd
)
#echo ${scriptpath}

function run_migu() {
  cn_name="tvbox-server"
  if docker ps -a | grep -q ${cn_name}; then docker rm -f ${cn_name}; fi

  docker run -d --restart=always --privileged --name ${cn_name} --network host \
    -e TZ='Asia/Shanghai' \
    -e PYTHONUNBUFFERED=0 \
    -v ${CODE_DIR}/backend:/app/backend \
    -v ${CODE_DIR}/spider:/app/spider \
    commi/tvbox:${TAG}
}

case "$1" in
run)
  run_migu
  ;;
*)
  echo "usage: $0 {run}"
  exit 1
  ;;
esac
