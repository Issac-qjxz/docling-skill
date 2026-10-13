"""真实 PDF、Docling 结构产物与子进程边界验证；固定随机种子 0。"""
import json
import random
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from pypdf import PdfWriter
from docling_core.types.doc import DoclingDocument, PageItem, DocItemLabel
from docling_core.types.doc.base import Size
import test_regressions
from test_regressions import options, converter, detector

random.seed(0)


class Validation(unittest.TestCase):
    setUp = test_regressions.Regressions.setUp

    def produce(self, cmd, **kwargs):
        directory = Path(cmd[cmd.index('--output') + 1])
        document = DoclingDocument(name='input')
        document.pages[1] = PageItem(page_no=1, size=Size(width=300, height=300))
        document.add_text(label=DocItemLabel.TEXT, text='Sample text')
        document.save_as_json(directory / 'input.json')
        (directory / 'input.md').write_bytes(b'Sample text')
        return subprocess.CompletedProcess(cmd, 0, '', 'WARNING: sample diagnostic')

    def test_valid_output_success_with_warning_and_log(self):
        with patch.object(converter.subprocess, 'run', side_effect=self.produce):
            result = converter.run_conversion(self.pdf, options(output=str(self.root)))
        self.assertTrue(result['success'], result['error'])
        self.assertEqual(result['quality']['pages'], 1)
        self.assertEqual(len(result['artifacts']), 2)
        self.assertIn('sample diagnostic', Path(result['log']).read_text(encoding='utf-8'))
        self.assertTrue(result['warnings'])

    def test_password_redaction_preserves_report_keys(self):
        with patch.object(converter.subprocess, 'run', side_effect=self.produce):
            result = converter.run_conversion(self.pdf, options(output=str(self.root), pdf_password='output'))
        self.assertTrue(result['success'], result['error'])
        self.assertIn('output_directory', result)
        self.assertNotIn('output', result['command'])

    def test_cli_report_is_utf8(self):
        result = subprocess.run([sys.executable, converter.__file__,
                                 str(self.root / 'missing.pdf'), '--json'],
                                capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertIn('文件不存在', report['error'])

    def test_info_logs_are_not_warnings(self):
        def produce(cmd, **kwargs):
            self.produce(cmd, **kwargs)
            return subprocess.CompletedProcess(cmd, 0, '', 'INFO: normal progress')
        with patch.object(converter.subprocess, 'run', side_effect=produce):
            result = converter.run_conversion(self.pdf, options(output=str(self.root)))
        self.assertTrue(result['success'], result['error'])
        self.assertEqual(result['warnings'], result['analysis']['warnings'])

    def test_json_missing_fails(self):
        def produce(cmd, **kwargs):
            completed = self.produce(cmd, **kwargs)
            directory = Path(cmd[cmd.index('--output') + 1])
            (directory / 'input.json').unlink()
            return completed
        with patch.object(converter.subprocess, 'run', side_effect=produce):
            result = converter.run_conversion(self.pdf, options(output=str(self.root)))
        self.assertFalse(result['success'])

    def test_wrong_page_count_fails(self):
        def produce(cmd, **kwargs):
            completed = self.produce(cmd, **kwargs)
            directory = Path(cmd[cmd.index('--output') + 1])
            path = directory / 'input.json'
            content = json.loads(path.read_text(encoding='utf-8'))
            content['pages'] = {}
            path.write_text(json.dumps(content), encoding='utf-8')
            return completed
        with patch.object(converter.subprocess, 'run', side_effect=produce):
            result = converter.run_conversion(self.pdf, options(output=str(self.root)))
        self.assertFalse(result['success'])
        self.assertIn('页面数量不一致', result['error'])

    def test_malformed_json_fails(self):
        def produce(cmd, **kwargs):
            completed = self.produce(cmd, **kwargs)
            directory = Path(cmd[cmd.index('--output') + 1])
            (directory / 'input.json').write_bytes(b'not json')
            return completed
        with patch.object(converter.subprocess, 'run', side_effect=produce):
            result = converter.run_conversion(self.pdf, options(output=str(self.root)))
        self.assertFalse(result['success'])

    def test_password_decrypts_before_analysis(self):
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        writer.encrypt('correct-password')
        with self.pdf.open('wb') as stream:
            writer.write(stream)
        locked = detector.detect_pdf_type(self.pdf)
        self.assertEqual(locked['error_code'], 'password_required')
        unlocked = detector.detect_pdf_type(self.pdf, password='correct-password')
        self.assertIsNone(unlocked['error'])
        self.assertEqual(unlocked['page_count'], 1)

    def test_timeout_keeps_failure_and_log(self):
        failure = subprocess.TimeoutExpired('docling', 30, output=b'partial log')
        with patch.object(converter.subprocess, 'run', side_effect=failure):
            result = converter.run_conversion(self.pdf, options(output=str(self.root)))
        self.assertFalse(result['success'])
        self.assertIn('超时', result['error'])
        self.assertIn('partial log', Path(result['log']).read_text(encoding='utf-8'))
