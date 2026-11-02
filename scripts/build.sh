#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p build
"${CXX:-c++}" -std=c++17 -O2 -pthread -Wall -Wextra -Wpedantic -Ibackend/include -Ibackend/vendor backend/src/main.cpp -lcurl -o build/navic-api
"${CXX:-c++}" -std=c++17 -O2 -pthread -Wall -Wextra -Wpedantic -Ibackend/include -Ibackend/vendor backend/tests/test_graph.cpp -o build/test-graph
./build/test-graph
