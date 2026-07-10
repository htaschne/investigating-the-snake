import ctypes
import importlib.util
import pathlib
import re
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_python_module():
  spec = importlib.util.spec_from_file_location("slices_py", ROOT / "slices.py")
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def load_c_library():
  temp_dir = tempfile.TemporaryDirectory()
  library_path = pathlib.Path(temp_dir.name) / "slices.so"
  subprocess.run(
    [
      "cc",
      "-std=c11",
      "-Wall",
      "-Wextra",
      "-Wpedantic",
      "-Wconversion",
      "-Wsign-conversion",
      "-fPIC",
      "-shared",
      "-o",
      str(library_path),
      str(ROOT / "slices.c"),
    ],
    check=True,
    cwd=ROOT,
  )

  library = ctypes.CDLL(str(library_path))
  library.slices.argtypes = [ctypes.c_int64]
  library.slices.restype = ctypes.c_int64
  library._temp_dir = temp_dir
  return library


def historical_record_holder_inputs():
  inputs = set()
  pattern = re.compile(r"found new best at: (\d+) =")
  for path in (ROOT / "results").glob("benchmark_*.txt"):
    for line in path.read_text().splitlines():
      match = pattern.search(line)
      if match:
        inputs.add(int(match.group(1)))
  return sorted(inputs)


class SlicesEquivalenceTest(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.python_module = load_python_module()
    cls.c_library = load_c_library()

  def assertPythonAndCAgree(self, n):
    python_result = self.python_module.slices(n)
    c_result = self.c_library.slices(n)

    self.assertIs(type(python_result), int)
    self.assertIs(type(c_result), int)
    self.assertEqual(python_result, c_result)

  def test_known_canonical_examples(self):
    examples = {
      0: 0,
      1: 1,
      2: 1,
      3: 2,
      9: 3,
      15: 4,
    }

    for n, expected in examples.items():
      with self.subTest(n=n):
        self.assertEqual(self.python_module.slices(n), expected)
        self.assertEqual(self.c_library.slices(n), expected)

  def test_python_and_c_agree_through_9999(self):
    for n in range(10000):
      with self.subTest(n=n):
        self.assertPythonAndCAgree(n)

  def test_historical_record_holder_inputs_agree(self):
    inputs = historical_record_holder_inputs()
    self.assertIn(1, inputs)
    self.assertIn(45045, inputs)

    for n in inputs:
      with self.subTest(n=n):
        self.assertPythonAndCAgree(n)


if __name__ == "__main__":
  unittest.main()
