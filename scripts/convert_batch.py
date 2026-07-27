"""
Docling Skill - 批量顺序转换脚本
遍历目录，按扩展名过滤，顺序调用 docling 转换。
并行由 SKILL.md 调度 Agent 实现，本脚本只负责顺序执行。

用法:
    python convert_batch.py ./docs/ --to md --output ./out/
    python convert_batch.py ./docs/ --to md --output ./out/ --ext pdf,docx
    python convert_batch.py ./docs/ --to json --output ./out/ --ext pdf --ocr-lang zh,en
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

from utils import verify_dir, print_summary


# 默认支持的扩展名
DEFAULT_EXTENSIONS = {
    'pdf', 'docx', 'pptx', 'xlsx', 'odt', 'ods', 'odp',
    'html', 'htm', 'epub', 'txt', 'md', 'tex',
    'png', 'jpg', 'jpeg', 'tiff', 'bmp',
    'wav', 'mp3', 'mp4', 'avi', 'mov', 'mkv', 'webm',
    'eml', 'msg', 'vtt', 'xbrl',
}


def collect_files(input_dir: Path, extensions: set) -> list:
    """
    收集目录下所有匹配扩展名的文件。

    Args:
        input_dir: 输入目录
        extensions: 允许的扩展名集合（小写，不含点号）

    Returns:
        list[Path]: 排序后的文件列表
    """
    files = []
    for f in input_dir.rglob('*'):
        if f.is_file() and f.suffix.lstrip('.').lower() in extensions:
            files.append(f)
    return sorted(files)


def build_cmd(filepath: Path, args) -> list:
    """构建单个文件的 docling 命令。"""
    cmd = ['docling', str(filepath)]

    if args.to:
        cmd.extend(['--to', args.to])
    if args.output:
        cmd.extend(['--output', str(args.output)])
    if getattr(args, 'from_fmt', None):
        cmd.extend(['--from', args.from_fmt])

    # PDF 选项
    if args.no_ocr:
        cmd.append('--no-ocr')
    if args.force_ocr:
        cmd.append('--force-ocr')
    if args.tables:
        cmd.append('--tables')
    if args.no_tables:
        cmd.append('--no-tables')
    if args.enrich_formula:
        cmd.append('--enrich-formula')
    if args.enrich_code:
        cmd.append('--enrich-code')
    if args.ocr_lang:
        cmd.extend(['--ocr-lang', args.ocr_lang])
    if args.ocr_engine:
        cmd.extend(['--ocr-engine', args.ocr_engine])
    if args.table_mode:
        cmd.extend(['--table-mode', args.table_mode])

    return cmd


def run_batch(input_dir: Path, args) -> tuple:
    """
    批量顺序转换。

    Returns:
        (total: int, success: int, failed: int, total_time: float)
    """
    # 解析扩展名
    if args.ext:
        extensions = set(e.strip().lstrip('.').lower() for e in args.ext.split(','))
    else:
        extensions = DEFAULT_EXTENSIONS

    files = collect_files(input_dir, extensions)

    if not files:
        print(f"No files found in {input_dir} with extensions: {extensions}")
        return 0, 0, 0, 0.0

    total = len(files)
    success = 0
    failed = 0
    start_all = time.time()

    for i, filepath in enumerate(files, 1):
        cmd = build_cmd(filepath, args)
        rel_path = filepath.relative_to(input_dir)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=600
            )
            if result.returncode == 0:
                success += 1
                print(f"[{i}/{total}] {rel_path} → OK", flush=True)
            else:
                failed += 1
                stderr = result.stderr.strip() if result.stderr else ""
                stdout = result.stdout.strip() if result.stdout else ""
                err = (stderr or stdout or "unknown error")[:200]
                print(f"[{i}/{total}] {rel_path} → FAILED | {err}", flush=True)
        except subprocess.TimeoutExpired:
            failed += 1
            print(f"[{i}/{total}] {rel_path} → FAILED | timeout (600s)", flush=True)
        except FileNotFoundError:
            failed += 1
            print(f"[{i}/{total}] {rel_path} → FAILED | docling not found", flush=True)
        except Exception as e:
            failed += 1
            print(f"[{i}/{total}] {rel_path} → FAILED | {e}", flush=True)

    total_time = time.time() - start_all
    return total, success, failed, total_time


def main():
    parser = argparse.ArgumentParser(
        description='Docling 批量顺序转换'
    )
    parser.add_argument('input', help='输入目录路径')
    parser.add_argument('--to', default='md',
                        choices=['md', 'json', 'yaml', 'html', 'html_split_page',
                                 'text', 'doctags', 'vtt', 'doclang', 'chunks'],
                        help='输出格式（默认 md）')
    parser.add_argument('--output', '-o', help='输出目录')
    parser.add_argument('--ext', help='文件扩展名过滤，逗号分隔（如 pdf,docx）')
    parser.add_argument('--from', dest='from_fmt', help='指定输入格式')

    # PDF 选项
    pdf_group = parser.add_argument_group('PDF options')
    pdf_group.add_argument('--no-ocr', action='store_true', help='禁用 OCR')
    pdf_group.add_argument('--force-ocr', action='store_true', help='强制 OCR')
    pdf_group.add_argument('--tables', action='store_true', help='启用表格结构提取')
    pdf_group.add_argument('--no-tables', action='store_true', help='禁用表格结构提取')
    pdf_group.add_argument('--enrich-formula', action='store_true', help='启用公式识别')
    pdf_group.add_argument('--enrich-code', action='store_true', help='启用代码块识别')
    pdf_group.add_argument('--ocr-lang', help='OCR 语言（如 zh,en）')
    pdf_group.add_argument('--ocr-engine', help='OCR 引擎')
    pdf_group.add_argument('--table-mode', choices=['fast', 'accurate'], help='表格模式')

    args = parser.parse_args()

    input_dir = verify_dir(args.input)

    if args.output:
        verify_dir(args.output)

    total, success, failed, total_time = run_batch(input_dir, args)
    print_summary(total, success, failed, total_time)
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
