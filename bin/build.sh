#!/bin/bash

set -e

GIT_COMMIT=$1
GIT_BRANCH=$2
GIT_PREVIOUS_SUCCESSFUL_COMMIT=$3

echo "Building ${GIT_COMMIT} from ${GIT_BRANCH}"
echo "Last build on this branch: ${GIT_PREVIOUS_SUCCESSFUL_COMMIT}"

./install || bin/run_python.sh araisan "AIのビルドに失敗したのだ。。。(コミット: ${GIT_COMMIT}, ブランチ: ${GIT_BRANCH})"

echo "Done"
bin/run_python.sh araisan "AIのビルドに成功したのだ！(コミット: ${GIT_COMMIT}, ブランチ: ${GIT_BRANCH})"
