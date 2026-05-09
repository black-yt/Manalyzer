import ast
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_DIRS = ['agents', 'tools', 'utils', 'workflow', 'webui']


def read_relative(path):
    return (PROJECT_ROOT / path).read_text(encoding='utf-8')


def iter_production_sources():
    for dirname in PRODUCTION_DIRS:
        for path in (PROJECT_ROOT / dirname).rglob('*.py'):
            yield path


class SourceContractsSmokeTest(unittest.TestCase):
    def test_no_bare_except_or_runtime_asserts_in_production_code(self):
        for path in iter_production_sources():
            tree = ast.parse(path.read_text(encoding='utf-8'))
            with self.subTest(path=str(path.relative_to(PROJECT_ROOT))):
                bare_except_lines = [
                    node.lineno
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ExceptHandler) and node.type is None
                ]
                assert_lines = [
                    node.lineno
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Assert)
                ]
                self.assertEqual(bare_except_lines, [])
                self.assertEqual(assert_lines, [])

    def test_webui_uses_shared_webui_data_directory(self):
        main_webui = read_relative('workflow/main_webui.py')
        webui = read_relative('webui/weiui.py')
        logger = read_relative('utils/logger.py')

        self.assertIn("os.path.join(REPO_ROOT, 'webui', 'data')", main_webui)
        self.assertIn("os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')", webui)
        self.assertIn("os.path.join(REPO_ROOT, 'webui', 'data')", logger)
        self.assertNotIn("'data/save_info.json'", webui)
        self.assertNotIn('max_workers=2', main_webui)

    def test_extraction_text_uses_real_newlines(self):
        source = read_relative('agents/data_extrator_checker.py')
        self.assertIn('"\\n".join(v)', source)
        self.assertNotIn(':/n', source)
        self.assertNotIn("'/n'.join", source)

    def test_scihub_is_lazy_loaded_by_wrappers(self):
        academic_search = read_relative('tools/academic_search.py')
        pdf_downloader = read_relative('tools/pdf_downloader.py')

        self.assertIn('sh = None', academic_search)
        self.assertIn('def get_scihub()', academic_search)
        self.assertIsNone(re.search(r'^sh\s*=\s*SciHub\(\)', academic_search, flags=re.MULTILINE))
        self.assertIn('sh = None', pdf_downloader)
        self.assertIn('def get_scihub()', pdf_downloader)
        self.assertIsNone(re.search(r'^sh\s*=\s*SciHub\(\)', pdf_downloader, flags=re.MULTILINE))

    def test_requests_in_tools_have_timeouts(self):
        for path in (PROJECT_ROOT / 'tools').rglob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if isinstance(node.func, ast.Attribute) and node.func.attr in {'get', 'urlopen'}:
                    call_text = ast.get_source_segment(path.read_text(encoding='utf-8'), node) or ''
                    if 'requests.' in call_text or '.sess.get' in call_text or 'urlopen' in call_text:
                        with self.subTest(path=str(path.relative_to(PROJECT_ROOT)), line=node.lineno):
                            self.assertTrue(
                                any(keyword.arg == 'timeout' for keyword in node.keywords),
                                call_text,
                            )


if __name__ == '__main__':
    unittest.main()
