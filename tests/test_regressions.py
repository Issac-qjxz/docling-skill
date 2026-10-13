"""单 PDF 流程回归测试；随机种子固定为 0，不下载模型。"""
import argparse
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pypdf import PdfWriter

random.seed(0)
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import detect_pdf_type as detector
import convert_single as converter
import utils


def options(**overrides):
    values = dict(to='md', output=None, from_fmt=None, no_ocr=False,
                  force_ocr=False, tables=False, no_tables=False,
                  enrich_formula=False, enrich_code=False,
                  enrich_chart_data=False, ocr_lang=None, ocr_engine='auto',
                  pdf_password=None, table_mode=None, pipeline=None,
                  vlm_model=None, timeout=30, sample_pages=7)
    values.update(overrides)
    return argparse.Namespace(**values)


class Page:
    def __init__(self, text='', images=False):
        self.text = text
        self.images = ['image'] if images else []
    def extract_text(self):
        return self.text
    def get(self, key, default=None):
        if key == '/Resources' and self.images:
            return {'/XObject': {'/Im1': {'/Subtype': '/Image'}}}
        return default


class Reader:
    is_encrypted = False
    trailer = {'/Root': {}}
    def __init__(self, pages):
        self.pages = pages
    def get_fields(self):
        return {}


class Regressions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pdf = self.root / 'input.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        with self.pdf.open('wb') as fp:
            writer.write(fp)

    def detect(self, pages, sample_pages=3):
        with patch.object(detector, 'PdfReader', return_value=Reader(pages)):
            return detector.detect_pdf_type(self.pdf, sample_pages)

    def test_invalid_pdf_is_not_encrypted(self):
        self.pdf.write_bytes(b'not a PDF')
        result = detector.detect_pdf_type(self.pdf)
        self.assertFalse(result['encrypted'])
        self.assertTrue(result.get('error'))

    def test_tail_scan_keeps_ocr(self):
        result = self.detect([Page('English content ' * 10)] * 3 + [Page(images=True)])
        self.assertNotIn('--no-ocr', result['recommended_flags'])

    def test_incomplete_sampling_keeps_ocr(self):
        result = self.detect([Page('English content ' * 10)] * 20)
        self.assertNotIn('--no-ocr', result['recommended_flags'])

    def test_scan_language_is_unknown(self):
        self.assertEqual(self.detect([Page(images=True)])['lang'], 'unknown')

    def test_blank_page_is_not_scan(self):
        self.assertEqual(self.detect([Page()])['type'], 'unknown')

    def test_non_pdf_is_rejected(self):
        path = self.root / 'input.docx'
        path.write_bytes(b'not PDF')
        with self.assertRaises((ValueError, SystemExit)):
            utils.verify_file(str(path))

    def test_output_directory_is_explicit(self):
        self.assertIn('--output', converter.build_docling_cmd(self.pdf, options()))

    def test_doclang_extension(self):
        path = converter._extract_output_path(self.pdf, options(to='doclang'))
        self.assertTrue(str(path).endswith('.dclg.xml'))

    def test_chunks_extension(self):
        path = converter._extract_output_path(self.pdf, options(to='chunks'))
        self.assertTrue(str(path).endswith('.chunks.jsonl'))

    def test_split_html_extension(self):
        path = converter._extract_output_path(self.pdf, options(to='html_split_page'))
        self.assertTrue(str(path).endswith('.html'))

    def test_zero_exit_without_artifact_fails(self):
        with patch.object(converter.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            result = converter.run_conversion(self.pdf, options(output=str(self.root)))
        self.assertFalse(result['success'] if isinstance(result, dict) else result[0])

    def test_old_artifact_does_not_count(self):
        (self.root / 'input.md').write_bytes(b'old output')
        with patch.object(converter.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            result = converter.run_conversion(self.pdf, options(output=str(self.root)))
        self.assertFalse(result['success'] if isinstance(result, dict) else result[0])

    def test_conflicting_ocr_flags_rejected(self):
        with self.assertRaises(ValueError):
            converter.build_docling_cmd(self.pdf, options(no_ocr=True, force_ocr=True))

    def test_chart_flag_matches_installed_cli(self):
        cmd = converter.build_docling_cmd(self.pdf, options(enrich_chart_data=True))
        self.assertIn('--enrich-chart-extraction', cmd)
        self.assertNotIn('--enrich-chart-data', cmd)


if __name__ == '__main__':
    unittest.main()