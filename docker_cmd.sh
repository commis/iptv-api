#!/bin/bash

SCRIPT_DIR=$(
  cd "$(dirname "$0")"
  pwd
)
cd "${SCRIPT_DIR}"

_user_help() {
  echo "脚本用途：Docker镜像的构建与推送快捷执行脚本"
  echo "============================================="
  echo "语法格式：$0 {build|push} [镜像版本]"
  echo "使用示例："
  echo "  1. 构建镜像：$0 build 1.0.20"
  echo "  2. 推送镜像：$0 push 1.0.20"
  echo "============================================="
  echo ""
  exit 1
}

docker_build() {
  image_tag=$1
  docker build -t commi/tvbox:${image_tag} .
  docker tag commi/tvbox:${image_tag} commi/tvbox:latest
}

docker_push() {
  image_tag=$1
  docker push commi/tvbox:${image_tag}
  docker push commi/tvbox:latest
}

if [ -z "$2" ]; then
  _user_help
fi

case "$1" in
build)
  docker_build "$2"
  ;;
push)
  docker_push "$2"
  ;;
*)
  _user_help
esac
