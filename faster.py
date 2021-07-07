#!/usr/bin/env python3

import sys

from ctypes import *

if __name__ == '__main__':
  # fast functions
  ff = CDLL(sys.argv[1])

  best = 0
  n = 100000
  for i in range(n):
    ret = ff.slices(i)
    if ret > best:
      best = ret
      print(f"found new best at: {i} = {ret}")
