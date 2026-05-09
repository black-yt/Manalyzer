import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


def install_fake_structai():
    fake = types.ModuleType('structai')

    def read_pdf(pdf_paths):
        fake.read_pdf_calls.append(list(pdf_paths))

    def save_file(obj, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=4)

    def get_all_file_paths(folder_path, prefix=None, suffix=None):
        paths = []
        for path in Path(folder_path).rglob('*'):
            if path.is_file():
                paths.append(str(path))
        if prefix is not None:
            paths = [path for path in paths if path.startswith(prefix)]
        if suffix is not None:
            paths = [path for path in paths if path.endswith(suffix)]
        return sorted(paths)

    fake.read_pdf_calls = []
    fake.read_pdf = read_pdf
    fake.save_file = save_file
    fake.get_all_file_paths = get_all_file_paths
    sys.modules['structai'] = fake
    return fake


class PaperParserSmokeTest(unittest.TestCase):
    def setUp(self):
        self.original_structai = sys.modules.get('structai')
        self.fake_structai = install_fake_structai()
        sys.modules.pop('agents.paper_parser', None)
        self.paper_parser_module = importlib.import_module('agents.paper_parser')

    def tearDown(self):
        sys.modules.pop('agents.paper_parser', None)
        if self.original_structai is None:
            sys.modules.pop('structai', None)
        else:
            sys.modules['structai'] = self.original_structai

    def test_empty_paper_info_writes_empty_content_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_dir = Path(tmp)
            (save_dir / '0_paper_info.json').write_text('{}', encoding='utf-8')

            parser = self.paper_parser_module.PaperParser(str(save_dir))
            parser()

            content_info = json.loads((save_dir / '1_content_list_info.json').read_text(encoding='utf-8'))
            self.assertEqual(content_info, {})
            self.assertEqual(self.fake_structai.read_pdf_calls, [])

    def test_missing_content_list_fails_with_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_dir = Path(tmp)
            pdf_path = save_dir / '0_pdf' / '00000.pdf'
            pdf_path.parent.mkdir()
            pdf_path.write_bytes(b'%PDF-1.4')
            (save_dir / '0_paper_info.json').write_text(
                json.dumps({'00000': {'pdf_path': str(pdf_path)}}),
                encoding='utf-8',
            )

            parser = self.paper_parser_module.PaperParser(str(save_dir))

            with self.assertRaises(FileNotFoundError):
                parser()


if __name__ == '__main__':
    unittest.main()
