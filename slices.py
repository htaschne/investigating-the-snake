#!/usr/bin/env python3

def slices(n: int) -> int:
  acc, a, b = 0, 0, 1
  while a < n:
    s = (a + b) * (b - a + 1) / 2;

    if s == n:
      acc += 1
      b += 1
    elif s < n:
      b += 1
    else:
      a += 1

  return acc + 1

if __name__ == '__main__':
  best = 0
  n = 100000
  for i in range(n):
    ret = slices(i)
    if ret > best:
      best = ret
      print(f"found new best at: {i} = {ret}")
