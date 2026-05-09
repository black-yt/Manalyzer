import tempfile
import unittest
from pathlib import Path

from utils.clean import clean_dict
from utils.file_name import basename_without_suffix, completed_or_not, get_all_file_paths, list_dir
from utils.knapsack import knapsack


class UtilsBehaviorSmokeTest(unittest.TestCase):
    def test_clean_dict_normalizes_and_filters_short_text(self):
        result = clean_dict({
            'A B': ['short', 'this is a long enough paragraph for the smoke test'],
            123: {'x': 1},
            'image': ['figure.jpg'],
        }, len_th=20)

        self.assertEqual(result['AB'], ['this is a long enough paragraph for the smoke test'])
        self.assertIn('123', result)
        self.assertEqual(result['image'], ['figure.jpg'])

    def test_file_name_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subdir = root / 'sub'
            subdir.mkdir()
            first = root / 'a.txt'
            second = subdir / 'b.json'
            first.write_text('a', encoding='utf-8')
            second.write_text('{}', encoding='utf-8')

            self.assertEqual(basename_without_suffix(str(first)), 'a')
            self.assertEqual([Path(p).name for p in list_dir(str(root))], ['a.txt', 'sub'])
            self.assertEqual([Path(p).name for p in get_all_file_paths(str(root), suffix='.json')], ['b.json'])
            self.assertEqual(Path(completed_or_not(str(root / 'b.pdf'), str(subdir))).name, 'b.json')

    def test_knapsack_selects_best_value_under_capacity(self):
        max_value, selected = knapsack([
            {'weight': 10, 'value': 2},
            {'weight': 8, 'value': 7},
            {'weight': 8, 'value': 8},
        ], 16)

        self.assertEqual(max_value, 15)
        self.assertEqual(selected, [0, 1, 1])


if __name__ == '__main__':
    unittest.main()
