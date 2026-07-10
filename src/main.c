#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#include "slices.h"

int main(void) {
  int64_t n = 100000;
  int64_t best = 0;
  for (int64_t i = 0; i < n; ++i) {
    int64_t ret = slices(i);
    if (ret > best) {
      printf("found new best at: %" PRId64 " = %" PRId64 "\n", i, ret);
      best = ret;
    }
  }
  return 0;
}
