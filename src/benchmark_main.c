#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "slices.h"

#define CHECKSUM_OFFSET UINT64_C(0x9e3779b97f4a7c15)
#define CHECKSUM_FACTOR UINT64_C(1315423911)

static uint64_t benchmark_checksum(int64_t limit) {
  uint64_t checksum = 0;
  for (int64_t i = 0; i < limit; ++i) {
    int64_t value = slices(i);
    checksum = checksum * CHECKSUM_FACTOR +
               (((uint64_t)value) ^ (((uint64_t)i) + CHECKSUM_OFFSET));
  }
  return checksum;
}

static int parse_limit(const char *text, int64_t *limit) {
  char *end = NULL;
  errno = 0;
  long long parsed = strtoll(text, &end, 10);
  if (errno != 0 || end == text || *end != '\0' || parsed < 0) {
    return 0;
  }
  *limit = (int64_t)parsed;
  return 1;
}

int main(int argc, char **argv) {
  int64_t limit = 100000;

  if (argc > 2) {
    fprintf(stderr, "usage: %s [limit]\n", argv[0]);
    return 2;
  }

  if (argc == 2 && !parse_limit(argv[1], &limit)) {
    fprintf(stderr, "invalid non-negative limit: %s\n", argv[1]);
    return 2;
  }

  printf("limit=%" PRId64 " checksum=%" PRIu64 "\n", limit, benchmark_checksum(limit));
  return 0;
}
