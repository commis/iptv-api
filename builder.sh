#!/bin/bash

TAG=latest

docker_build() {
  docker build -t commi/tvbox:${TAG} .
}

docker_push() {
  docker push commi/tvbox:${TAG}
}
