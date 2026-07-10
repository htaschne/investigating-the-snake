#!/bin/sh
set -eu

repo_root=$(CDPATH= cd "$(dirname "$0")" && pwd)
build_dir="$repo_root/build"

mkdir -p "$build_dir"

case "$(uname -s)" in
  Darwin)
    output="$build_dir/libslices.dylib"
    shared_flags="-dynamiclib -fPIC"
    ;;
  Linux)
    output="$build_dir/libslices.so"
    shared_flags="-shared -fPIC"
    ;;
  *)
    echo "unsupported platform: $(uname -s)" >&2
    exit 1
    ;;
esac

# Keep Phase 2 neutral and explicit; benchmark-tuned flags belong later.
cc \
  -std=c11 \
  -Wall \
  -Wextra \
  -Wpedantic \
  -Wconversion \
  -Wsign-conversion \
  -O0 \
  -I"$repo_root/include" \
  $shared_flags \
  -o "$output" \
  "$repo_root/src/slices.c"

echo "$output"
