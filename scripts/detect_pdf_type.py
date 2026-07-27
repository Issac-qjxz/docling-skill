"""
Docling Skill - PDF 深度分析脚本
检测 PDF 类型（矢量/扫描/混合/学术/表单/加密），
识别语言（中/英），输出推荐转换参数。

用法:
    python detect_pdf_type.py input.pdf
    python detect_pdf_type.py input.pdf --json
    python detect_pdf_type.py input.pdf --sample-pages 5
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ── pypdf：PDF 结构分析 ──────────────────────────────────────────────
from pypdf import PdfReader

# ── 本地工具 ─────────────────────────────────────────────────────────
from utils import verify_file, get_file_size_mb, format_output


# ── 常量 ──────────────────────────────────────────────────────────────
# 中文字符 Unicode 范围（CJK Unified Ideographs 基本区 + 扩展A区）
RE_CHINESE = re.compile(r'[一-鿿㐀-䶿]')
# LaTeX 公式特征符号
FORMULA_PATTERNS = [
    r'\\frac', r'\\int', r'\\sum', r'\\prod', r'\\sqrt',
    r'\\alpha', r'\\beta', r'\\gamma', r'\\delta',
    r'\\begin\{equation', r'\\begin\{align', r'\\begin\{math',
    r'\$\$[^$]+\$\$',  # display math
]
RE_FORMULA = re.compile('|'.join(FORMULA_PATTERNS))

# 类型优先级（从高到低判定）
PDF_TYPES = {
    'encrypted':  '加密 PDF，需要密码才能读取',
    'form':       '包含表单字段的 PDF',
    'scanned':    '扫描件，无文本层，需要 OCR',
    'academic':   '学术论文，含公式',
    'mixed':      '图文混排，含文本和图片',
    'vector_text': '纯矢量文字 PDF',
    'unknown':    '无法判定类型',
}

# 类型 → 推荐 docling 参数
TYPE_FLAGS = {
    'vector_text': ['--no-ocr', '--tables'],
    'scanned':     ['--force-ocr', '--tables'],
    'mixed':       ['--tables'],
    'academic':    ['--tables', '--enrich-formula'],
    'form':        ['--tables'],  # form 类型不做 OCR 假设，由后续逻辑根据文本层决定
    'encrypted':   [],
    'unknown':     ['--tables'],
}


def detect_pdf_type(filepath: Path, sample_pages: int = 3) -> dict:
    """
    深度分析 PDF，返回类型、特征、推荐参数。

    Args:
        filepath: PDF 文件路径
        sample_pages: 采样前 N 页用于语言和内容检测

    Returns:
        dict: 包含所有检测结果的字典
    """
    result = {
        'file': str(filepath),
        'type': 'unknown',
        'has_text_layer': False,
        'has_images': False,
        'has_formulas': False,
        'page_count': 0,
        'encrypted': False,
        'form_fields': False,
        'lang': 'en',
        'lang_confidence': 0.0,
        'file_size_mb': round(get_file_size_mb(filepath), 2),
        'recommended_flags': [],
    }

    # ── 1. 基础检查：加密 ─────────────────────────────────────────
    try:
        reader = PdfReader(str(filepath))
    except Exception as e:
        # 可能是加密或损坏
        result['type'] = 'encrypted'
        result['encrypted'] = True
        result['recommended_flags'] = ['--pdf-password <PASSWORD>']
        return result

    if reader.is_encrypted:
        result['type'] = 'encrypted'
        result['encrypted'] = True
        result['recommended_flags'] = ['--pdf-password <PASSWORD>']
        return result

    result['page_count'] = len(reader.pages)

    # ── 2. 表单检测 ───────────────────────────────────────────────
    try:
        if '/AcroForm' in reader.trailer.get('/Root', {}):
            result['form_fields'] = True
    except Exception:
        pass

    # ── 3. 逐页采样分析 ───────────────────────────────────────────
    total_chars = 0
    chinese_chars = 0
    total_text_len = 0
    has_image = False
    has_formula = False

    pages_to_check = min(sample_pages, result['page_count'])

    for i in range(pages_to_check):
        page = reader.pages[i]

        # 提取文本
        try:
            text = page.extract_text() or ''
        except Exception:
            text = ''

        text_len = len(text.strip())
        total_text_len += text_len

        # 统计中文字符
        for ch in text:
            if ch.strip():
                total_chars += 1
            if RE_CHINESE.match(ch):
                chinese_chars += 1

        # 检测公式
        if RE_FORMULA.search(text):
            has_formula = True

        # 检测图片
        try:
            if hasattr(page, 'images') and page.images:
                has_image = True
            elif '/XObject' in page.get('/Resources', {}):
                xobjects = page['/Resources']['/XObject']
                for obj_name in xobjects:
                    xobj = xobjects[obj_name]
                    if hasattr(xobj, 'get') and xobj.get('/Subtype') == '/Image':
                        has_image = True
                        break
        except Exception:
            pass

    result['has_text_layer'] = total_text_len > 50  # 至少 50 字符才算有文本层
    result['has_images'] = has_image
    result['has_formulas'] = has_formula

    # ── 4. 语言检测 ───────────────────────────────────────────────
    if total_chars > 0:
        zh_ratio = chinese_chars / total_chars
        result['lang_confidence'] = round(zh_ratio, 3)
        if zh_ratio > 0.1:
            result['lang'] = 'zh'
        else:
            result['lang'] = 'en'
    else:
        result['lang'] = 'en'
        result['lang_confidence'] = 0.0

    # ── 5. 综合类型判定 ───────────────────────────────────────────
    if result['form_fields']:
        result['type'] = 'form'
    elif not result['has_text_layer']:
        result['type'] = 'scanned'
    elif result['has_formulas']:
        result['type'] = 'academic'
    elif result['has_images']:
        result['type'] = 'mixed'
    elif result['has_text_layer']:
        result['type'] = 'vector_text'
    else:
        result['type'] = 'unknown'

    # ── 6. 推荐参数 ───────────────────────────────────────────────
    flags = list(TYPE_FLAGS.get(result['type'], []))

    # form 类型特殊处理：无文本层时需要 OCR
    if result['type'] == 'form' and not result['has_text_layer']:
        flags.insert(0, '--force-ocr')

    # 语言参数：中文文档加 --ocr-lang（适用于需要 OCR 的场景）
    if result['lang'] == 'zh' and result['type'] in ('scanned', 'mixed', 'form'):
        flags.extend(['--ocr-lang', 'zh,en'])

    result['recommended_flags'] = flags

    return result


def main():
    parser = argparse.ArgumentParser(
        description='PDF 深度分析：检测类型、语言，推荐转换参数'
    )
    parser.add_argument('input', help='PDF 文件路径')
    parser.add_argument('--json', action='store_true',
                        help='以 JSON 格式输出')
    parser.add_argument('--sample-pages', type=int, default=3,
                        help='采样页数（默认 3）')
    args = parser.parse_args()

    filepath = verify_file(args.input)
    result = detect_pdf_type(filepath, sample_pages=args.sample_pages)
    print(format_output(result, as_json=args.json))


if __name__ == '__main__':
    main()
