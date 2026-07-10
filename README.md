# Python is really fun... but it's also slow sometimes. What if it could run faster?

## Motivation
Don't you like when you can code in a high level, interpreted, super cool and disruptive language without the disadvantages of it? Me too.

## Experiment
> C is a systems programming language with low overhead in the runtime as the compiler tries to minimize it, so it must be one of the fastest languages to run programs.
> Python is an interpreted language which focus on readability and writability with a lot of overhead in the runtime, so it should be slower than C.
> If I could call C from Python how much faster could it get?

So the experiment consists in implementing the same algorithm in C and Python and comparing the time each of them takes with the time the Python version which calls C takes.

## Setup
For the test I've used a costly function which generates the [number of divisors of highly composite odd numbers](https://oeis.org/A053640) up until ```100000```. It's not optimized on purpose.

## Benchmarking
I've used the ```time``` program to measure the time each program takes. The results I've found are in the ```benchmark_``` files.

## Build and run
```bash
make
make run
make ffi
make test
make check
make benchmark-smoke
make benchmark
```

Generated artifacts are written under `build/`. The default build currently uses `-O0` so the standalone executable and shared library share the same explicit baseline; benchmark-oriented optimization comparisons are still future work. Build flags can be overridden, for example:

```bash
make clean
make CFLAGS="-std=c11 -O2 -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion"
```

The historical timings below are preserved as context and are not yet a reproducible benchmark.

## Reproducible benchmarks
```bash
make benchmark-smoke
make benchmark
make benchmark-analyze
make benchmark-asm
```

`make benchmark-smoke` is a quick non-authoritative check. `make benchmark` rebuilds standalone C and ctypes benchmark artifacts for `-O0`, `-O1`, `-O2`, `-O3`, and `-Os`, verifies matching checksums, and writes timestamped JSON under `benchmarks/results/`. The default Makefile benchmark excludes pure Python so routine runs do not take the historical long path; include it explicitly with:

```bash
make benchmark BENCH_INCLUDE_PYTHON=--include-python
```

The benchmark limit, warmups, runs, and seed can be overridden with `BENCH_LIMIT`, `BENCH_WARMUPS`, `BENCH_RUNS`, and `BENCH_SEED`. Benchmarks depend on hardware, compiler, workload, and system load, so JSON results are generated artifacts rather than final claims.

## Results
The  C compiled with ```-O2``` optimization always takes ```37 seconds``` on my machine, not once it got down to 36 or up to 38 in 100 tests. The Python version finishes at the ```20 minutes``` mark with less than a minute of _floatuation_. Calling C from Python raises some questions because it's faster than the C code itself!? It finish at the ```16 seconds``` mark.

## Reasoning
 I could not found why calling C from Python is faster than pure C. I imagine that for a larger input that may change, but I can't test that on my machine as it takes forever to finish. Another thing that comes to mind is that maybe there are some optimizations that Python does that are not enabled in C by default. I don't know, needs further investigation, if you have any ideas I'd be happy to try it out!

## Resources
I've followed [this](https://www.journaldev.com/31907/calling-c-functions-from-python) tutorial to learn how to compile and call C from Python.
