#!/bin/sh
set -eu

repo_root=$(CDPATH= cd "$(dirname "$0")" && pwd)
make -C "$repo_root" --no-print-directory shared
