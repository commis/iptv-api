#!/bin/bash

ROOT_DIR=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)

function del_history_commit() {
    git checkout --orphan latest_branch
    git add -A
    git commit -am "commit message"
    git branch -D main
    git branch -m main
    git push -f origin main
    git branch --set-upstream-to=origin/main main
}

# main function code
OLD=$(pwd)
del_history_commit
cd "$OLD" || exit
