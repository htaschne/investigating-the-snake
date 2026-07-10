#!/usr/bin/env python3

import sys
from pathlib import Path

import ctypes


def default_library_path() -> Path:
  suffix = ".dylib" if sys.platform == "darwin" else ".so"
  return Path(__file__).resolve().parent / "build" / f"libslices{suffix}"


if __name__ == '__main__':
  library_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_library_path()
  if not library_path.exists():
    print(f"library not found: {library_path}", file=sys.stderr)
    print("run ./create_so_file.sh or pass an explicit library path", file=sys.stderr)
    sys.exit(1)

  try:
    ff = ctypes.CDLL(str(library_path))
  except OSError as exc:
    print(f"could not load library {library_path}: {exc}", file=sys.stderr)
    sys.exit(1)

  ff.slices.argtypes = [ctypes.c_int64]
  ff.slices.restype = ctypes.c_int64

  best = 0
  n = 100000
  for i in range(n):
    ret = ff.slices(i)
    if ret > best:
      best = ret
      print(f"found new best at: {i} = {ret}")
