#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def format_duration(ns):
  if ns is None:
    return "-"
  if ns >= 1_000_000_000:
    return f"{ns / 1_000_000_000:.3f}s"
  if ns >= 1_000_000:
    return f"{ns / 1_000_000:.3f}ms"
  if ns >= 1_000:
    return f"{ns / 1_000:.3f}us"
  return f"{ns}ns"


def format_size(size):
  if size is None:
    return "-"
  if size >= 1024 * 1024:
    return f"{size / (1024 * 1024):.1f} MiB"
  if size >= 1024:
    return f"{size / 1024:.1f} KiB"
  return f"{size} B"


def load_result(path):
  with Path(path).open() as handle:
    return json.load(handle)


def case_label(case):
  opt = case.get("optimization")
  return opt if opt is not None else "-"


def main():
  parser = argparse.ArgumentParser(description="Print a benchmark summary table.")
  parser.add_argument("result", help="Path to a benchmark JSON result file")
  args = parser.parse_args()

  result = load_result(args.result)
  cases = [case for case in result["cases"] if case.get("status") == "ok"]
  if not cases:
    raise SystemExit("no successful cases in result")

  baseline = next(
    (
      case for case in cases
      if case["implementation"] == "standalone-c" and case.get("optimization") == "O0"
    ),
    cases[0],
  )
  baseline_ns = baseline["statistics"]["median_ns"]
  fastest = min(cases, key=lambda case: case["statistics"]["median_ns"])
  slowest = max(cases, key=lambda case: case["statistics"]["median_ns"])
  python_included = any(case["implementation"] == "pure-python" for case in result["cases"])

  print(f"Result: {args.result}")
  print(f"Timestamp: {result.get('timestamp')}")
  print(f"Git commit: {result.get('git', {}).get('commit')} dirty={result.get('git', {}).get('dirty')}")
  print(f"Limit: {result.get('config', {}).get('limit')} runs={result.get('config', {}).get('runs')} warmups={result.get('config', {}).get('warmups')}")
  print(f"Pure Python included: {python_included}")
  print()
  print(f"{'Implementation':<16} {'Opt':<4} {'Median':>10} {'Mean':>10} {'Std dev':>10} {'Relative':>10} {'Size':>10}")
  print("-" * 78)
  for case in sorted(cases, key=lambda item: (item["implementation"], str(item.get("optimization")))):
    median = case["statistics"]["median_ns"]
    relative = baseline_ns / median if median else 0
    print(
      f"{case['implementation']:<16} "
      f"{case_label(case):<4} "
      f"{format_duration(median):>10} "
      f"{format_duration(case['statistics']['mean_ns']):>10} "
      f"{format_duration(case['statistics']['stdev_ns']):>10} "
      f"{relative:>9.2f}x "
      f"{format_size(case.get('artifact_size_bytes')):>10}"
    )

  print()
  print(
    "Fastest: "
    f"{fastest['implementation']} {case_label(fastest)} "
    f"({format_duration(fastest['statistics']['median_ns'])})"
  )
  print(
    "Slowest: "
    f"{slowest['implementation']} {case_label(slowest)} "
    f"({format_duration(slowest['statistics']['median_ns'])})"
  )
  print("Do not infer statistical significance from this summary alone.")


if __name__ == "__main__":
  main()
