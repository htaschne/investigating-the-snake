#!/usr/bin/env python3

import sys

import ctypes

if __name__ == '__main__':
  # fast functions
  ff = ctypes.CDLL(sys.argv[1])
  ff.slices.argtypes = [ctypes.c_int64]
  ff.slices.restype = ctypes.c_int64

  best = 0
  n = 100000
  for i in range(n):
    ret = ff.slices(i)
    if ret > best:
      best = ret
      print(f"found new best at: {i} = {ret}")
