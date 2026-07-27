"""
Docling Skill - 单文件转换脚本
纯执行器：接收参数，调用 docling 转换，返回结果。
不做任何自动检测，完全信任调用者传入的参数。

用法:
    python convert_single.py input.pdf --to md --output ./out/
    python convert_single.py input.pdf --to json --no-ocr --tables
    python convert_single.py input.pdf --to md --force-ocr --ocr-lang zh,en
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

from utils import verify_file, verify_dir, print_result


def build_docling_cmd(input_file: Path, args) -> list:
    """
    构建 docling CLI 命令。

    Args:
        input_file: 输入文件路径
        args: argparse 解析后的参数

    Returns:
        list: 命令列表
    """
    cmd = ['docling', str(input_file)]

    # 输出格式
    if args.to:
        cmd.extend(['--to', args.to])

    # 输出目录
    if args.output:
        cmd.extend(['--output', str(args.output)])

    # 输入格式
    if getattr(args, 'from_fmt', None):
        cmd.extend(['--from', args.from_fmt])

    # PDF 相关
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
    if args.enrich_chart_data:
        cmd.append('--enrich-chart-data')
    if args.ocr_lang:
        cmd.extend(['--ocr-lang', args.ocr_lang])
    if args.ocr_engine:
        cmd.extend(['--ocr-engine', args.ocr_engine])
    if args.pdf_password:
        cmd.extend(['--pdf-password', args.pdf_password])
    if args.table_mode:
        cmd.extend(['--table-mode', args.table_mode])

    # VLM 管线
    if args.pipeline:
        cmd.extend(['--pipeline', args.pipeline])
    if args.vlm_model:
        cmd.extend(['--vlm-model', args.vlm_model])

    return cmd


def run_conversion(input_file: Path, args) -> tuple:
    """
    执行单文件转换。

    Returns:
        (success: bool, output_path: str|None, error: str|None, elapsed: float)
    """
    cmd = build_docling_cmd(input_file, args)

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=600  # 10 分钟超时
        )
        elapsed = time.time() - start

        if result.returncode == 0:
            # 从输出中提取生成的文件路径
            output_path = _extract_output_path(input_file, args)
            return True, output_path, None, elapsed
        else:
            stderr = result.stderr.strip() if result.stderr else ""
            stdout = result.stdout.strip() if result.stdout else ""
            error = stderr or stdout or f"exit code {result.returncode}"
            # 截断过长的错误信息
            if len(error) > 500:
                error = error[:500] + "..."
            return False, None, error, elapsed

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return False, None, "Conversion timed out (600s)", elapsed
    except FileNotFoundError:
        elapsed = time.time() - start
        return False, None, "docling command not found. Is Docling installed?", elapsed
    except Exception as e:
        elapsed = time.time() - start
        return False, None, str(e), elapsed


def _extract_output_path(input_file: Path, args) -> str:
    """推断输出文件路径。"""
    output_dir = Path(args.output) if args.output else input_file.parent
    ext_map = {
        'md': '.md', 'json': '.json', 'yaml': '.yaml',
        'html': '.html', 'text': '.txt', 'doctags': '.doctags',
        'vtt': '.vtt', 'doclang': '.doclang',
    }
    ext = ext_map.get(args.to, '.md') if args.to else '.md'
    output_file = output_dir / (input_file.stem + ext)
    return str(output_file)


def main():
    parser = argparse.ArgumentParser(
        description='Docling 单文件转换（纯执行器，不做自动检测）'
    )
    parser.add_argument('input', help='输入文件路径')
    parser.add_argument('--to', default='md',
                        choices=['md', 'json', 'yaml', 'html', 'html_split_page',
                                 'text', 'doctags', 'vtt', 'doclang', 'chunks'],
                        help='输出格式（默认 md）')
    parser.add_argument('--output', '-o', help='输出目录（默认当前目录）')
    parser.add_argument('--from', dest='from_fmt', help='指定输入格式')

    # PDF 选项
    pdf_group = parser.add_argument_group('PDF options')
    pdf_group.add_argument('--no-ocr', action='store_true', help='禁用 OCR')
    pdf_group.add_argument('--force-ocr', action='store_true', help='强制 OCR')
    pdf_group.add_argument('--tables', action='store_true', help='启用表格结构提取')
    pdf_group.add_argument('--no-tables', action='store_true', help='禁用表格结构提取')
    pdf_group.add_argument('--enrich-formula', action='store_true', help='启用公式识别')
    pdf_group.add_argument('--enrich-code', action='store_true', help='启用代码块识别')
    pdf_group.add_argument('--enrich-chart-data', action='store_true', help='启用图表数据提取')
    pdf_group.add_argument('--ocr-lang', help='OCR 语言（如 zh,en）')
    pdf_group.add_argument('--ocr-engine', help='OCR 引擎（tesseract/easyocr/rapidocr）')
    pdf_group.add_argument('--pdf-password', help='PDF 密码')
    pdf_group.add_argument('--table-mode', choices=['fast', 'accurate'], help='表格模式')

    # VLM 选项
    vlm_group = parser.add_argument_group('VLM options')
    vlm_group.add_argument('--pipeline', choices=['standard', 'vlm', 'asr'],
                           help='处理管线')
    vlm_group.add_argument('--vlm-model', help='VLM 模型名称')

    args = parser.parse_args()

    # 验证输入
    input_file = verify_file(args.input)

    # 验证输出目录
    if args.output:
        verify_dir(args.output)

    # 执行转换
    success, output_path, error, elapsed = run_conversion(input_file, args)
    print_result(str(input_file), success, elapsed, output_path, error)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
