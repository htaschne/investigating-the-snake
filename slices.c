#include <stdio.h>
#include <stddef.h>

int64_t slices(int64_t n) {
  int64_t a = 1, b = 2, acc = 0;
  while (a < n) {
    int64_t s = (a + b) * (b - a + 1) / 2;
    if (s == n) {
      acc++;
      b++;
    } else if (s < n) {
      b++;
    } else {
      a++;
    }
  }
  return acc + 1;
}

int main() {
  int32_t n = 100000;
  int32_t best = 0;
  for (int64_t i = 0; i < n; ++i) {
    int64_t ret = slices(i);
    if (ret > best) {
      printf("found new best at: %lld = %lld\n", i, ret);
      best = ret;
    }
  }
  return 0;
}
