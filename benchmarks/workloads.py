import ctypes
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKSUM_OFFSET = 0x9E3779B97F4A7C15
CHECKSUM_FACTOR = 1315423911
UINT64_MASK = (1 << 64) - 1


def load_python_slices():
  spec = importlib.util.spec_from_file_location("slices_py", ROOT / "slices.py")
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module.slices


def load_ctypes_slices(library_path):
  library = ctypes.CDLL(str(library_path))
  library.slices.argtypes = [ctypes.c_int64]
  library.slices.restype = ctypes.c_int64
  return library.slices


def update_checksum(checksum, index, value):
  return (
    checksum * CHECKSUM_FACTOR
    + (int(value) ^ (int(index) + CHECKSUM_OFFSET))
  ) & UINT64_MASK


def checksum_for_slices(slices_func, limit):
  checksum = 0
  for index in range(limit):
    checksum = update_checksum(checksum, index, slices_func(index))
  return checksum
