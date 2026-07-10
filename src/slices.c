#include "slices.h"

int64_t slices(int64_t n) {
  if (n <= 0) {
    return 0;
  }

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
