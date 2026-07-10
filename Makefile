CC ?= cc
PYTHON ?= python3

UNAME_S := $(shell uname -s)

BUILD_DIR := build
BIN_DIR := $(BUILD_DIR)/bin
LIB_DIR := $(BUILD_DIR)/lib
OBJ_DIR := $(BUILD_DIR)/obj

TARGET := $(BIN_DIR)/investigating-the-snake

ifeq ($(UNAME_S),Darwin)
  SHARED_EXT := dylib
  SHARED_LDFLAGS := -dynamiclib
else ifeq ($(UNAME_S),Linux)
  SHARED_EXT := so
  SHARED_LDFLAGS := -shared
else
  $(error unsupported platform: $(UNAME_S))
endif

SHARED_LIB := $(LIB_DIR)/libslices.$(SHARED_EXT)

CPPFLAGS ?= -Iinclude
# Phase 3 keeps the baseline explicit and neutral; optimization comparisons belong to benchmarks.
CFLAGS ?= -std=c11 -O0 -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion
LDFLAGS ?=

MAIN_OBJ := $(OBJ_DIR)/main.o
SLICES_OBJ := $(OBJ_DIR)/slices.o
SLICES_PIC_OBJ := $(OBJ_DIR)/slices.pic.o

PYTHON_SOURCES := faster.py slices.py tests/test_equivalence.py benchmarks/analyze.py benchmarks/run.py benchmarks/workloads.py
BENCH_LIMIT ?= 100000
BENCH_WARMUPS ?= 1
BENCH_RUNS ?= 5
BENCH_SEED ?= 42
BENCH_INCLUDE_PYTHON ?=

.PHONY: all run shared ffi test check clean benchmark-smoke benchmark benchmark-analyze benchmark-asm

all: $(TARGET) $(SHARED_LIB)

run: $(TARGET)
	$(TARGET)

shared: $(SHARED_LIB)
	@echo $(SHARED_LIB)

ffi: $(SHARED_LIB)
	$(PYTHON) faster.py $(SHARED_LIB)

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests

check: all test
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m py_compile $(PYTHON_SOURCES)
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git diff --check; fi

benchmark-smoke:
	@echo "Non-authoritative smoke benchmark; use make benchmark for repeated measurements."
	$(PYTHON) benchmarks/run.py --limit 1000 --warmups 0 --runs 1 --seed $(BENCH_SEED)

benchmark:
	$(PYTHON) benchmarks/run.py --limit $(BENCH_LIMIT) --warmups $(BENCH_WARMUPS) --runs $(BENCH_RUNS) --seed $(BENCH_SEED) --generate-asm $(BENCH_INCLUDE_PYTHON)

benchmark-analyze:
	@if [ -z "$(RESULT)" ]; then \
		result=$$(ls -t benchmarks/results/*.json 2>/dev/null | head -n 1); \
		if [ -z "$$result" ]; then echo "set RESULT=path or run make benchmark first" >&2; exit 1; fi; \
	else \
		result="$(RESULT)"; \
	fi; \
	$(PYTHON) benchmarks/analyze.py "$$result"

benchmark-asm:
	$(PYTHON) benchmarks/run.py --generate-asm --asm-only

clean:
	rm -rf $(BUILD_DIR) __pycache__ tests/__pycache__ benchmarks/__pycache__

$(TARGET): $(MAIN_OBJ) $(SLICES_OBJ) | $(BIN_DIR)
	$(CC) $(LDFLAGS) $(MAIN_OBJ) $(SLICES_OBJ) -o $@

$(SHARED_LIB): $(SLICES_PIC_OBJ) | $(LIB_DIR)
	$(CC) $(LDFLAGS) $(SHARED_LDFLAGS) $(SLICES_PIC_OBJ) -o $@

$(MAIN_OBJ): src/main.c include/slices.h | $(OBJ_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c src/main.c -o $@

$(SLICES_OBJ): src/slices.c include/slices.h | $(OBJ_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c src/slices.c -o $@

$(SLICES_PIC_OBJ): src/slices.c include/slices.h | $(OBJ_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -fPIC -c src/slices.c -o $@

$(BIN_DIR) $(LIB_DIR) $(OBJ_DIR):
	mkdir -p $@
