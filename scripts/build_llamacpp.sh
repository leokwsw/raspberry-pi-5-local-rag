#!/usr/bin/env bash
set -euo pipefail
target="${1:-third_party/llama.cpp}"
if [[ ! -d "$target/.git" ]]; then
  git clone --depth 1 https://github.com/ggml-org/llama.cpp "$target"
fi
cmake -S "$target" -B "$target/build" -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS
cmake --build "$target/build" --config Release -j"$(nproc)"
