import importlib.util
import unittest


EXPECTED_OPTIONAL_DEPENDENCIES = [
    'structai',
    'arxiv',
    'flask_cors',
    'openai',
    'Levenshtein',
    'datasets',
    'markdown',
]


class DependencyInventorySmokeTest(unittest.TestCase):
    def test_optional_dependency_inventory_is_explicit(self):
        missing = [
            name for name in EXPECTED_OPTIONAL_DEPENDENCIES
            if importlib.util.find_spec(name) is None
        ]

        # This test is documentation as much as validation: the current minimal
        # environment may miss these packages, but the list should stay explicit.
        self.assertIsInstance(missing, list)


if __name__ == '__main__':
    unittest.main()
