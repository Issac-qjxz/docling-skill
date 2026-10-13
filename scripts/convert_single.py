"""单 PDF 完整转换流程；独立输出目录、结构验证与可审计结果。不使用随机抽样。"""
import argparse
import copy
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from detect_pdf_type import detect_pdf_type
from utils import verify_file, verify_dir, format_output

EXTENSIONS = {'md': '.md', 'json': '.json', 'yaml': '.yaml', 'html': '.html',
              'html_split_page': '.html', 'text': '.txt', 'doctags': '.doctags',
              'doclang': '.dclg.xml', 'chunks': '.chunks.jsonl'}


def build_docling_cmd(input_file: Path, args) -> list:
    if args.no_ocr and args.force_ocr:
        raise ValueError('--no-ocr 与 --force-ocr 不能同时使用。')
    if args.tables and args.no_tables:
        raise ValueError('--tables 与 --no-tables 不能同时使用。')
    if args.to not in EXTENSIONS:
        raise ValueError('不支持该 PDF 输出格式。')
    engine = getattr(args, 'ocr_engine', None) or 'auto'
    if getattr(args, 'ocr_lang', None) and engine == 'auto':
        raise ValueError('指定 --ocr-lang 时也必须指定 --ocr-engine，语言代码因引擎而异。')
    output = Path(args.output).resolve() if args.output else input_file.parent.resolve()
    cmd = [sys.executable, '-X', 'utf8', '-m', 'docling.cli.main', 'convert', str(input_file),
           '--from', 'pdf', '--pipeline', 'standard', '--to', args.to,
           '--output', str(output), '--abort-on-error', '--image-export-mode', 'embedded']
    if args.to != 'json':
        cmd.extend(['--to', 'json'])  # 始终导出结构副本，用于页数和内容验证。
    for enabled, flag in [(args.no_ocr, '--no-ocr'), (args.force_ocr, '--force-ocr'),
                          (args.tables, '--tables'), (args.no_tables, '--no-tables'),
                          (args.enrich_formula, '--enrich-formula'),
                          (args.enrich_code, '--enrich-code'),
                          (getattr(args, 'enrich_chart_data', False), '--enrich-chart-extraction')]:
        if enabled:
            cmd.append(flag)
    cmd.extend(['--ocr-engine', engine])
    for name, flag in [('ocr_lang', '--ocr-lang'), ('pdf_password', '--pdf-password'),
                       ('table_mode', '--table-mode')]:
        value = getattr(args, name, None)
        if value:
            cmd.extend([flag, value])
    return cmd


def _extract_output_path(input_file: Path, args) -> str:
    directory = Path(args.output) if args.output else input_file.parent
    return str(directory / (input_file.stem + EXTENSIONS[args.to]))


def _validate_artifacts(input_file, args, page_count):
    from docling_core.types.doc import DoclingDocument
    requested = Path(_extract_output_path(input_file, args))
    structural = Path(args.output) / (input_file.stem + '.json')
    artifacts = list(dict.fromkeys([requested, structural]))
    for path in artifacts:
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'缺少输出或输出为空：{path.name}')
    doc = DoclingDocument.model_validate_json(structural.read_text(encoding='utf-8'))
    if len(doc.pages) != page_count:
        raise ValueError(f'页面数量不一致：输入 {page_count} 页，结构输出 {len(doc.pages)} 页。')
    if args.to == 'chunks':
        for line in requested.read_text(encoding='utf-8').splitlines():
            if line.strip():
                json.loads(line)
    elif args.to == 'yaml':
        import yaml
        DoclingDocument.model_validate(yaml.safe_load(requested.read_text(encoding='utf-8')))
    warnings = []
    if not any(item.text.strip() for item in doc.texts) and not doc.tables:
        warnings.append('未提取到正文或表格，请检查空白页、OCR 和图片内容。')
    return artifacts, dict(pages=len(doc.pages), text_items=len(doc.texts),
                          tables=len(doc.tables), pictures=len(doc.pictures)), warnings


def run_conversion(input_file: Path, args) -> dict:
    start = time.monotonic()
    report = dict(success=False, input=str(input_file), output_directory=None,
                  artifacts=[], analysis=None, warnings=[], error=None, elapsed_seconds=0.0)
    password = getattr(args, 'pdf_password', None)
    def redact(value):
        text = str(value)
        return text.replace(password, '<REDACTED>') if password else text
    try:
        input_file = verify_file(str(input_file))
        report['input'] = str(input_file)
        analysis = detect_pdf_type(input_file, getattr(args, 'sample_pages', 7), password)
        report['analysis'] = analysis
        report['warnings'].extend(analysis['warnings'])
        if analysis['error']:
            raise ValueError(analysis['error'])
        effective = copy.copy(args)
        # 用户显式指定的 OCR 和表格选项优先于检测建议。
        if not effective.no_ocr and not effective.force_ocr:
            effective.no_ocr = '--no-ocr' in analysis['recommended_flags']
            effective.force_ocr = '--force-ocr' in analysis['recommended_flags']
        if not effective.tables and not effective.no_tables:
            effective.tables = True
        build_docling_cmd(input_file, effective)  # 创建输出目录之前检查参数冲突。
        if getattr(args, 'timeout', 600) <= 0:
            raise ValueError('超时秒数必须大于 0。')
        version = importlib.metadata.version('docling')
        report['docling_version'] = version
        if version != '2.115.0':
            report['warnings'].append(f'当前 Docling {version}；本技能已验证版本为 2.115.0。')
        parent = verify_dir(str(args.output or input_file.parent))
        # 每次创建独立目录，旧文件不能进入本次成功判定，也不覆盖既有结果。
        effective.output = tempfile.mkdtemp(prefix=input_file.stem + '_docling_', dir=parent)
        report['output_directory'] = effective.output
        cmd = build_docling_cmd(input_file, effective)
        report['command'] = [redact(item) for item in cmd]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                                errors='replace', timeout=getattr(args, 'timeout', 600))
        report['exit_code'] = result.returncode
        diagnostics = redact((result.stdout or '') + '\n' + (result.stderr or ''))
        log_path = Path(effective.output) / 'conversion.log'
        log_path.write_text(diagnostics, encoding='utf-8')
        report['log'] = str(log_path)
        if result.returncode != 0:
            raise ValueError(f'Docling 退出码 {result.returncode}；详情见 {log_path}')
        if re.search(r'warning|error|exception|failed', result.stderr or '', re.IGNORECASE):
            report['warnings'].append('Docling 日志包含警告或错误，完整内容保存在 conversion.log。')
        artifacts, quality, warnings = _validate_artifacts(input_file, effective, analysis['page_count'])
        report['quality'] = quality
        report['warnings'].extend(warnings)
        report['artifacts'] = [dict(path=str(path), bytes=path.stat().st_size) for path in artifacts]
        report['success'] = True
    except subprocess.TimeoutExpired as exc:
        report['error'] = f'转换超时（{getattr(args, "timeout", 600)} 秒）。'
        if report['output_directory']:
            chunks = []
            for value in (exc.stdout, exc.stderr):
                if value:
                    chunks.append(value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value)
            log_path = Path(report['output_directory']) / 'conversion.log'
            log_path.write_text(redact('\n'.join(chunks)), encoding='utf-8')
            report['log'] = str(log_path)
    except importlib.metadata.PackageNotFoundError:
        report['error'] = '当前 Python 环境没有 Docling；安装技能目录下的 requirements.txt。'
    except Exception as exc:
        report['error'] = redact(f'{type(exc).__name__}: {exc}')
    report['elapsed_seconds'] = round(time.monotonic() - start, 3)
    # 密码不进入分析、命令、诊断或报告文件。
    if report['analysis'] and report['analysis']['error']:
        report['analysis']['error'] = redact(report['analysis']['error'])
    if report['output_directory']:
        path = Path(report['output_directory']) / 'conversion-report.json'
        path.write_text(format_output(report, True) + '\n', encoding='utf-8')
    return report


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='仅转换一个本地 PDF：自动分析并验证输出')
    parser.add_argument('input', help='单个本地 PDF 路径')
    parser.add_argument('--to', default='md', choices=list(EXTENSIONS))
    parser.add_argument('--output', '-o', help='输出父目录；默认 PDF 所在目录，每次创建独立子目录')
    parser.add_argument('--json', action='store_true', help='以 JSON 输出转换报告')
    parser.add_argument('--sample-pages', type=int, default=7)
    parser.add_argument('--timeout', type=float, default=600)
    ocr = parser.add_mutually_exclusive_group()
    ocr.add_argument('--no-ocr', action='store_true')
    ocr.add_argument('--force-ocr', action='store_true')
    tables = parser.add_mutually_exclusive_group()
    tables.add_argument('--tables', action='store_true')
    tables.add_argument('--no-tables', action='store_true')
    parser.add_argument('--enrich-formula', action='store_true')
    parser.add_argument('--enrich-code', action='store_true')
    parser.add_argument('--enrich-chart-extraction', '--enrich-chart-data', dest='enrich_chart_data', action='store_true')
    parser.add_argument('--ocr-engine', default='auto', choices=['auto', 'rapidocr', 'easyocr', 'tesseract', 'tesseract_cli'])
    parser.add_argument('--ocr-lang', help='所选 OCR 引擎的语言代码；auto 引擎不接受语言覆盖')
    parser.add_argument('--pdf-password', help='PDF 密码；建议使用环境变量 DOCLING_PDF_PASSWORD')
    parser.add_argument('--table-mode', choices=['fast', 'accurate'])
    args = parser.parse_args()
    if args.pdf_password is None:
        args.pdf_password = os.environ.get('DOCLING_PDF_PASSWORD')
    report = run_conversion(Path(args.input), args)
    print(format_output(report, args.json))
    return 0 if report['success'] else 1


if __name__ == '__main__':
    sys.exit(main())
