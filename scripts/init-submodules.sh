#!/bin/bash

SCRIPT_DIR=$(
  cd $(dirname $0)
  pwd
)
PROJECT_DIR=$(
  cd ${SCRIPT_DIR}/..
  pwd
)

cd ${PROJECT_DIR}
git submodule init
git submodule update

# 进入子模块目录，配置稀疏检出
cd spider
git config core.sparseCheckout true
cat <<EOF >../.git/modules/spider/info/sparse-checkout
dist/
service.yaml
EOF
git checkout main
