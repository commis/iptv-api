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
echo "dist/" >../.git/modules/spider/info/sparse-checkout
echo "service.yaml" >>../.git/modules/spider/info/sparse-checkout
git checkout main
