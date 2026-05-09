import importlib
import unittest


DEPENDENCY_LIGHT_MODULES = [
    'tools.scihub',
    'utils.clean',
    'utils.file_name',
    'utils.knapsack',
    'utils.logger',
]


class ImportSmokeTest(unittest.TestCase):
    def test_dependency_light_modules_import(self):
        for module_name in DEPENDENCY_LIGHT_MODULES:
            with self.subTest(module=module_name):
                importlib.import_module(module_name)


if __name__ == '__main__':
    unittest.main()
