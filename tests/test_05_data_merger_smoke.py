import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


def install_fake_dependencies():
    structai = types.ModuleType('structai')

    class LLMAgent:
        def __init__(self, *args, **kwargs):
            pass

        def safe_api(self, **kwargs):
            return kwargs.get('return_example', [])

    def multi_thread(inputs, fn):
        return [fn(**item) for item in inputs]

    structai.LLMAgent = LLMAgent
    structai.multi_thread = multi_thread
    sys.modules['structai'] = structai

    levenshtein = types.ModuleType('Levenshtein')
    levenshtein.distance = lambda a, b: 0 if a == b else 100
    sys.modules['Levenshtein'] = levenshtein


class DataMergerSmokeTest(unittest.TestCase):
    def setUp(self):
        self.original_structai = sys.modules.get('structai')
        self.original_levenshtein = sys.modules.get('Levenshtein')
        install_fake_dependencies()
        sys.modules.pop('agents.data_merger', None)
        self.data_merger_module = importlib.import_module('agents.data_merger')

    def tearDown(self):
        sys.modules.pop('agents.data_merger', None)
        if self.original_structai is None:
            sys.modules.pop('structai', None)
        else:
            sys.modules['structai'] = self.original_structai
        if self.original_levenshtein is None:
            sys.modules.pop('Levenshtein', None)
        else:
            sys.modules['Levenshtein'] = self.original_levenshtein

    def test_merges_table_and_ignores_none_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_dir = Path(tmp)
            integrated_path = save_dir / 'paper.json'
            integrated_path.write_text(json.dumps({
                'table': {
                    'integrated_table': (
                        '| River | Location | Heavy metals | Content (ug/L) |\n'
                        '|---|---|---|---|\n'
                        '| Tigris | Turkey | Cu | 40 |\n'
                    )
                },
                'text': 'None',
            }), encoding='utf-8')
            (save_dir / '5_integrated_table_info.json').write_text(json.dumps({
                '00000': {'integrated_table_path': str(integrated_path)}
            }), encoding='utf-8')

            merger = self.data_merger_module.DataMerger(str(save_dir))
            template = (
                '| River | Location | Heavy metals | Content (ug/L) |\n'
                '|---|---|---|---|\n'
                '| Example | Example | Cu | 1 |\n'
            )
            merged = merger.get_merge_integrated_table(template)

            self.assertEqual(list(merged.columns), ['River', 'Location', 'Heavy metals', 'Content (ug/L)', 'Reference'])
            self.assertEqual(merged.iloc[0]['River'].strip(), 'Tigris')
            self.assertEqual(merged.iloc[0]['Reference'], '00000')

    def test_refine_empty_table_returns_without_llm_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_dir = Path(tmp)
            (save_dir / '5_integrated_table_info.json').write_text('{}', encoding='utf-8')
            merger = self.data_merger_module.DataMerger(str(save_dir))

            empty = merger.get_merge_integrated_table('| A |\n|---|\n')
            refined = merger.refine_table(empty)

            self.assertTrue(refined.empty)


if __name__ == '__main__':
    unittest.main()
