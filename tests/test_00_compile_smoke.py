import py_compile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', '__pycache__', '.pytest_cache'}


def iter_python_files():
    for path in PROJECT_ROOT.rglob('*.py'):
        if any(part in SKIP_DIRS for part in path.relative_to(PROJECT_ROOT).parts):
            continue
        yield path


class CompileSmokeTest(unittest.TestCase):
    def test_all_python_files_compile(self):
        for path in iter_python_files():
            with self.subTest(path=str(path.relative_to(PROJECT_ROOT))):
                py_compile.compile(str(path), doraise=True)


if __name__ == '__main__':
    unittest.main()
