# Investigating the Snake

Five years ago, I ran a small experiment and concluded that Python calling C through `ctypes` was faster than a standalone C program.

That result was wrong. This repository is the investigation into why.

## The Experiment

The program scans integers and counts how many ways each one can be written as a sum of one or more consecutive positive integers. For example:

```text
9 = 9
9 = 4 + 5
9 = 2 + 3 + 4
```

So `slices(9) = 3`.

This count is related to the number of odd divisors of an integer, and the record-setting values line up with [OEIS A053640](https://oeis.org/A053640). The algorithm here is intentionally direct rather than mathematically optimized, because the project is about implementation boundaries and benchmarking.

The original comparison was:

1. Pure Python.
2. Standalone C.
3. Python calling the C implementation through `ctypes`.

## What Went Wrong

The historical result files in `results/` are preserved as artifacts, but they are not reliable benchmark evidence. The modernization found several problems:

- The Python and C implementations were not initially equivalent.
- Python used floating-point division where the C code used integer division.
- The `ctypes` boundary relied on default argument and return types instead of explicit signed 64-bit declarations.
- The standalone executable and shared library were built with different flags.
- The benchmark used shell timings without warmups, repeated runs, correctness gates, or build provenance.

In short: the benchmark was the bug.

## Verified Result

With equivalent builds and a shared checksum, standalone C and Python-through-`ctypes` now produce the same results. On the tested machine, optimized C builds were substantially faster than `-O0`, and `ctypes` overhead was small relative to this workload.

Reference environment:

- Apple Clang 17.0.0
- Darwin 25.5.0
- arm64
- Python 3.13.13
- Workload: `slices(n)` for `0 <= n < 100000`
- Warmups: 1
- Measured runs: 5
- Checksum: `14011015563422644207`
- Result file: `benchmarks/results/reference-darwin-arm64-clang17.json`

Representative medians from that result, using standalone C `-O0` as the baseline:

| Implementation | Optimization | Median | Relative |
| --- | ---: | ---: | ---: |
| Standalone C | `-O0` | 11.781 s | 1.00x |
| Standalone C | `-O1` | 4.298 s | 2.74x |
| Standalone C | `-O2` | 4.394 s | 2.68x |
| Standalone C | `-O3` | 4.307 s | 2.74x |
| Standalone C | `-Os` | 6.319 s | 1.86x |
| `ctypes` | `-O0` | 11.330 s | 1.04x |
| `ctypes` | `-O1` | 4.314 s | 2.73x |
| `ctypes` | `-O2` | 4.317 s | 2.73x |
| `ctypes` | `-O3` | 4.322 s | 2.73x |
| `ctypes` | `-Os` | 6.320 s | 1.86x |

This does not mean `ctypes` has zero overhead, and it does not say anything universal about C optimization. It says that the old conclusion was not supported, and that for this implementation on this machine, the optimized builds were about 2.6x faster than `-O0`.

## How It Works

The C implementation exposes a small public API:

```c
int64_t slices(int64_t n);
```

The standalone executable and benchmark executable both call that API. The Python FFI runner loads the generated shared library with `ctypes` and declares:

```python
argtypes = [ctypes.c_int64]
restype = ctypes.c_int64
```

Equivalence tests compile a temporary shared library, load it through `ctypes`, and compare C against Python for known examples, historical record-holder inputs, and every value from `0` through `9999`.

## Build and Run

```bash
make
make run
make ffi
make test
make check
```

Generated binaries and libraries go under `build/`. The default developer build uses `-O0` as an explicit baseline. You can override flags when needed:

```bash
make clean
make CFLAGS="-std=c11 -O2 -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion"
```

The compatibility script still works, but delegates to the Makefile:

```bash
./create_so_file.sh
```

## Benchmarking

Quick smoke check:

```bash
make benchmark-smoke
```

Standard repeated benchmark:

```bash
make benchmark
make benchmark-analyze
```

Generate assembly for inspection:

```bash
make benchmark-asm
```

`make benchmark` rebuilds standalone C and `ctypes` artifacts for `-O0`, `-O1`, `-O2`, `-O3`, and `-Os`, verifies matching checksums, randomizes execution order with a deterministic seed, and writes timestamped JSON files under `benchmarks/results/`. Generated benchmark binaries and assembly live under `build/`.

Pure Python is excluded by default because the original workload is much slower. For a quick pure-Python check, include it explicitly with a smaller workload:

```bash
make benchmark BENCH_LIMIT=1000 BENCH_WARMUPS=0 BENCH_RUNS=3 BENCH_INCLUDE_PYTHON=--include-python
```

For an authoritative pure-Python comparison, use the same limit and repetition policy as the other implementations. You can adjust the workload with:

```bash
make benchmark BENCH_LIMIT=25000 BENCH_WARMUPS=1 BENCH_RUNS=5
```

Generated timestamped benchmark sessions are ignored by Git. The committed reference result is intentionally selected for documentation.

## Project Structure

```text
.
├── include/       # Public C API
├── src/           # C library and executable entry points
├── tests/         # Python/C equivalence tests
├── benchmarks/    # Benchmark harness, analysis, and selected reference result
├── results/       # Original historical timings
├── Makefile
└── README.md
```

## Notes and Limitations

- Results are machine-, compiler-, workload-, and environment-specific.
- Scheduler noise, thermal state, and CPU frequency behavior are not fully controlled.
- The benchmark harness times standalone C as a subprocess, so process startup is included there; Python and `ctypes` workloads run in-process.
- The algorithm is intentionally not replaced with the best mathematical shortcut.
- This project compares these execution paths for this implementation, not the best possible implementation of the underlying mathematical function.

The next useful step is not adding more languages. It is keeping the story honest: correctness first, reproducible builds second, benchmark claims last.
