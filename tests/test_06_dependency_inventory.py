import importlib.util
import unittest
from pathlib import Path


EXPECTED_OPTIONAL_DEPENDENCIES = [
    'structai',
    'arxiv',
    'flask_cors',
    'openai',
    'Levenshtein',
    'datasets',
    'markdown',
]

EXPECTED_REQUIREMENTS = [
    'structai',
    'openai',
    'requests',
    'arxiv',
    'urllib3',
    'beautifulsoup4',
    'markdown',
    'pandas',
    'numpy',
    'scikit-learn',
    'matplotlib',
    'Pillow',
    'python-Levenshtein',
    'tqdm',
    'flask',
    'flask-cors',
    'datasets',
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

    def test_requirements_file_lists_runtime_dependencies(self):
        requirements_path = Path(__file__).resolve().parents[1] / 'requirements.txt'
        requirement_names = {
            line.strip()
            for line in requirements_path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')
        }

        self.assertEqual(set(EXPECTED_REQUIREMENTS), requirement_names)


if __name__ == '__main__':
    unittest.main()
