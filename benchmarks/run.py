#!/usr/bin/env python3

import argparse
import json
import os
import platform
import random
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from workloads import checksum_for_slices, load_ctypes_slices, load_python_slices


ROOT = Path(__file__).resolve().parents[1]
OPTIMIZATIONS = ("O0", "O1", "O2", "O3", "Os")
ASM_OPTIMIZATIONS = ("O0", "O2", "O3")
WARNING_FLAGS = ("-Wall", "-Wextra", "-Wpedantic", "-Wconversion", "-Wsign-conversion")
KNOWN_VALUES = {
  0: 0,
  1: 1,
  2: 1,
  3: 2,
  9: 3,
  15: 4,
}


def shared_extension():
  if sys.platform == "darwin":
    return "dylib"
  if sys.platform.startswith("linux"):
    return "so"
  raise SystemExit(f"unsupported platform: {sys.platform}")


def shared_link_flags():
  if sys.platform == "darwin":
    return ["-dynamiclib"]
  if sys.platform.startswith("linux"):
    return ["-shared"]
  raise SystemExit(f"unsupported platform: {sys.platform}")


def run_command(command, *, cwd=ROOT, capture=True):
  return subprocess.run(
    command,
    cwd=cwd,
    check=True,
    text=True,
    capture_output=capture,
  )


def command_output(command):
  try:
    return run_command(command).stdout.strip()
  except (OSError, subprocess.CalledProcessError):
    return None


def git_metadata():
  commit = command_output(["git", "rev-parse", "HEAD"])
  status = command_output(["git", "status", "--porcelain"])
  return {
    "commit": commit or "unknown",
    "dirty": bool(status),
  }


def cpu_description():
  if sys.platform == "darwin":
    value = command_output(["sysctl", "-n", "machdep.cpu.brand_string"])
    if value:
      return value
    processor = platform.processor()
    machine = platform.machine()
    return " ".join(part for part in (processor, machine) if part) or "unknown"
  if sys.platform.startswith("linux"):
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
      for line in cpuinfo.read_text(errors="replace").splitlines():
        if line.lower().startswith("model name"):
          return line.split(":", 1)[1].strip()
  return platform.processor() or "unknown"


def compiler_version(cc):
  try:
    completed = run_command([cc, "--version"])
    return completed.stdout.strip().splitlines()
  except (OSError, subprocess.CalledProcessError):
    return ["unknown"]


def system_metadata(cc):
  return {
    "os": platform.system(),
    "os_release": platform.release(),
    "architecture": platform.machine(),
    "machine": platform.platform(),
    "python_version": sys.version,
    "compiler": shutil.which(cc) or cc,
    "compiler_version": compiler_version(cc),
    "cpu": cpu_description(),
  }


def base_cflags(optimization):
  return ["-std=c11", f"-{optimization}", *WARNING_FLAGS]


def build_for_optimization(cc, optimization):
  bench_dir = ROOT / "build" / "bench" / optimization
  obj_dir = bench_dir / "obj"
  bin_dir = bench_dir / "bin"
  lib_dir = bench_dir / "lib"
  for directory in (obj_dir, bin_dir, lib_dir):
    directory.mkdir(parents=True, exist_ok=True)

  executable = bin_dir / "benchmark-slices"
  library = lib_dir / f"libslices.{shared_extension()}"
  commands = []

  def run_build(command):
    commands.append(command)
    run_command(command, capture=True)

  cflags = base_cflags(optimization)
  cppflags = ["-Iinclude"]
  slices_obj = obj_dir / "slices.o"
  slices_pic_obj = obj_dir / "slices.pic.o"
  benchmark_obj = obj_dir / "benchmark_main.o"

  run_build([cc, *cppflags, *cflags, "-c", "src/slices.c", "-o", str(slices_obj)])
  run_build([cc, *cppflags, *cflags, "-c", "src/benchmark_main.c", "-o", str(benchmark_obj)])
  run_build([cc, str(benchmark_obj), str(slices_obj), "-o", str(executable)])
  run_build([cc, *cppflags, *cflags, "-fPIC", "-c", "src/slices.c", "-o", str(slices_pic_obj)])
  run_build([cc, *shared_link_flags(), str(slices_pic_obj), "-o", str(library)])

  return {
    "optimization": optimization,
    "executable": executable,
    "library": library,
    "build_commands": commands,
    "executable_size_bytes": executable.stat().st_size,
    "library_size_bytes": library.stat().st_size,
  }


def generate_assembly(cc):
  asm_dir = ROOT / "build" / "bench" / "asm"
  asm_dir.mkdir(parents=True, exist_ok=True)
  outputs = []
  for optimization in ASM_OPTIMIZATIONS:
    path = asm_dir / f"slices-{optimization}.s"
    command = [
      cc,
      "-Iinclude",
      *base_cflags(optimization),
      "-S",
      "src/slices.c",
      "-o",
      str(path),
    ]
    run_command(command)
    outputs.append({"optimization": optimization, "path": str(path), "command": command})
  return outputs


def parse_standalone_output(output):
  match = re.fullmatch(r"limit=(\d+) checksum=(\d+)", output.strip())
  if not match:
    raise RuntimeError(f"unexpected benchmark output: {output!r}")
  return int(match.group(1)), int(match.group(2))


def run_standalone(case, limit):
  start = time.perf_counter_ns()
  completed = run_command([str(case["executable"]), str(limit)])
  duration = time.perf_counter_ns() - start
  output_limit, checksum = parse_standalone_output(completed.stdout)
  if output_limit != limit:
    raise RuntimeError(f"limit mismatch: expected {limit}, got {output_limit}")
  return duration, checksum


def run_ctypes(case, limit):
  slices_func = case.setdefault("ctypes_func", load_ctypes_slices(case["library"]))
  start = time.perf_counter_ns()
  checksum = checksum_for_slices(slices_func, limit)
  duration = time.perf_counter_ns() - start
  return duration, checksum


def run_python(case, limit):
  slices_func = case.setdefault("python_func", load_python_slices())
  start = time.perf_counter_ns()
  checksum = checksum_for_slices(slices_func, limit)
  duration = time.perf_counter_ns() - start
  return duration, checksum


def statistics_for(durations):
  return {
    "median_ns": int(statistics.median(durations)),
    "mean_ns": int(statistics.mean(durations)),
    "stdev_ns": int(statistics.stdev(durations)) if len(durations) > 1 else 0,
    "min_ns": int(min(durations)),
    "max_ns": int(max(durations)),
  }


def make_cases(builds, include_python):
  cases = []
  for build in builds:
    optimization = build["optimization"]
    cases.append({
      "id": f"standalone-c-{optimization}",
      "implementation": "standalone-c",
      "optimization": optimization,
      "executable": build["executable"],
      "artifact_size_bytes": build["executable_size_bytes"],
      "build_commands": build["build_commands"],
    })
    cases.append({
      "id": f"ctypes-{optimization}",
      "implementation": "ctypes",
      "optimization": optimization,
      "library": build["library"],
      "artifact_size_bytes": build["library_size_bytes"],
      "build_commands": build["build_commands"],
    })
  if include_python:
    cases.append({
      "id": "pure-python",
      "implementation": "pure-python",
      "optimization": None,
      "artifact_size_bytes": None,
      "build_commands": [],
    })
  return cases


def run_case(case, limit):
  if case["implementation"] == "standalone-c":
    return run_standalone(case, limit)
  if case["implementation"] == "ctypes":
    return run_ctypes(case, limit)
  if case["implementation"] == "pure-python":
    return run_python(case, limit)
  raise RuntimeError(f"unknown implementation: {case['implementation']}")


def validate_known_values():
  slices_func = load_python_slices()
  for n, expected in KNOWN_VALUES.items():
    actual = slices_func(n)
    if actual != expected:
      raise RuntimeError(f"known value mismatch for slices({n}): expected {expected}, got {actual}")


def correctness_gate(cases, limit):
  checksums = {}
  for case in cases:
    _, checksum = run_case(case, limit)
    checksums[case["id"]] = checksum
  expected = next(iter(checksums.values()))
  mismatches = {
    case_id: checksum
    for case_id, checksum in checksums.items()
    if checksum != expected
  }
  if mismatches:
    raise RuntimeError(f"checksum mismatch: expected {expected}, got {mismatches}")
  return expected, checksums


def measured_runs(cases, limit, warmups, runs, seed):
  rng = random.Random(seed)
  execution_order = []
  durations = {case["id"]: [] for case in cases}

  for iteration in range(warmups):
    order = list(cases)
    rng.shuffle(order)
    execution_order.append({
      "phase": "warmup",
      "iteration": iteration,
      "case_ids": [case["id"] for case in order],
    })
    for case in order:
      run_case(case, limit)

  for iteration in range(runs):
    order = list(cases)
    rng.shuffle(order)
    execution_order.append({
      "phase": "measured",
      "iteration": iteration,
      "case_ids": [case["id"] for case in order],
    })
    for case in order:
      duration, checksum = run_case(case, limit)
      if checksum != cases[0]["checksum"]:
        raise RuntimeError(f"checksum changed for {case['id']}: {checksum}")
      durations[case["id"]].append(duration)

  return durations, execution_order


def write_result(result, results_dir):
  results_dir.mkdir(parents=True, exist_ok=True)
  timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
  path = results_dir / f"benchmark-{timestamp}.json"
  with path.open("w") as handle:
    json.dump(result, handle, indent=2)
    handle.write("\n")
  return path


def build_result(args, builds, cases, checksum, checksum_by_case, durations, execution_order, asm_outputs):
  clean_cases = []
  for case in cases:
    clean_cases.append({
      "id": case["id"],
      "implementation": case["implementation"],
      "optimization": case["optimization"],
      "checksum": str(case["checksum"]),
      "artifact_size_bytes": case["artifact_size_bytes"],
      "durations_ns": durations[case["id"]],
      "statistics": statistics_for(durations[case["id"]]),
      "build_commands": [" ".join(command) for command in case["build_commands"]],
      "status": "ok",
    })

  return {
    "schema_version": 1,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "git": git_metadata(),
    "system": system_metadata(args.cc),
    "config": {
      "limit": args.limit,
      "warmups": args.warmups,
      "runs": args.runs,
      "seed": args.seed,
      "include_python": args.include_python,
      "timing_authority": "python time.perf_counter_ns",
      "standalone_c_process_startup_included": True,
      "ctypes_and_python_in_process": True,
    },
    "workload": {
      "checksum_algorithm": "uint64 checksum = checksum * 1315423911 + (slices(i) ^ (i + 0x9e3779b97f4a7c15))",
      "expected_checksum": str(checksum),
      "checksum_by_case": {case_id: str(value) for case_id, value in checksum_by_case.items()},
    },
    "builds": [
      {
        "optimization": build["optimization"],
        "executable": str(build["executable"]),
        "library": str(build["library"]),
        "executable_size_bytes": build["executable_size_bytes"],
        "library_size_bytes": build["library_size_bytes"],
        "commands": [" ".join(command) for command in build["build_commands"]],
      }
      for build in builds
    ],
    "assembly": asm_outputs,
    "execution_order": execution_order,
    "cases": clean_cases,
  }


def main():
  parser = argparse.ArgumentParser(description="Run reproducible slices benchmarks.")
  parser.add_argument("--limit", type=int, default=100000, help="exclusive upper bound for slices inputs")
  parser.add_argument("--warmups", type=int, default=2, help="warmup repetitions per case")
  parser.add_argument("--runs", type=int, default=7, help="measured repetitions per case")
  parser.add_argument("--seed", type=int, default=42, help="deterministic execution-order seed")
  parser.add_argument("--include-python", action="store_true", help="include the slow pure-Python workload")
  parser.add_argument("--cc", default=os.environ.get("CC", "cc"), help="C compiler")
  parser.add_argument("--results-dir", type=Path, default=ROOT / "benchmarks" / "results")
  parser.add_argument("--generate-asm", action="store_true", help="generate assembly for O0, O2, and O3")
  parser.add_argument("--asm-only", action="store_true", help="only generate assembly and exit")
  args = parser.parse_args()

  if args.limit < 0 or args.warmups < 0 or args.runs < 1:
    raise SystemExit("limit and warmups must be non-negative; runs must be at least 1")

  validate_known_values()
  asm_outputs = generate_assembly(args.cc) if args.generate_asm or args.asm_only else []
  for asm in asm_outputs:
    print(f"assembly {asm['optimization']}: {asm['path']}")
  if args.asm_only:
    return

  builds = [build_for_optimization(args.cc, optimization) for optimization in OPTIMIZATIONS]
  cases = make_cases(builds, args.include_python)

  checksum, checksum_by_case = correctness_gate(cases, args.limit)
  for case in cases:
    case["checksum"] = checksum_by_case[case["id"]]

  durations, execution_order = measured_runs(cases, args.limit, args.warmups, args.runs, args.seed)
  result = build_result(args, builds, cases, checksum, checksum_by_case, durations, execution_order, asm_outputs)
  path = write_result(result, args.results_dir)
  print(f"benchmark result: {path}")
  print(f"checksum: {checksum}")
  print("timing note: standalone C includes process startup; ctypes and pure Python are timed in-process.")


if __name__ == "__main__":
  main()
