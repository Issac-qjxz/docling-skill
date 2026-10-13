"""PDF 启发式分析：确定性分散采样，不将未知语言或解析错误伪装成已知类型。"""
import argparse
import re
import sys
from pathlib import Path
from pypdf import PdfReader
from utils import verify_file, get_file_size_mb, format_output

RE_CHINESE = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')
RE_LATIN = re.compile(r'[A-Za-z]')
RE_FORMULA = re.compile(r'\\(?:frac|int|sum|sqrt|begin\{(?:equation|align))|[∑∫√]|\b[A-Za-z]\s*=\s*[^\n]{1,40}[²³^]')


def _contains_image(page):
    """只检查资源结构，不解码页面图片。"""
    visited = set()
    def visit(resources):
        if hasattr(resources, 'get_object'):
            resources = resources.get_object()
        objects = resources.get('/XObject', {}) if resources else {}
        if hasattr(objects, 'get_object'):
            objects = objects.get_object()
        for reference in objects.values():
            obj = reference.get_object() if hasattr(reference, 'get_object') else reference
            identity = id(obj)
            if identity in visited:
                continue
            visited.add(identity)
            if obj.get('/Subtype') == '/Image':
                return True
            if obj.get('/Subtype') == '/Form' and visit(obj.get('/Resources', {})):
                return True
        return False
    return visit(page.get('/Resources', {}))


def detect_pdf_type(filepath: Path, sample_pages: int = 7, password=None) -> dict:
    result = dict(file=str(filepath), type='unknown', has_text_layer=False,
                  has_images=False, has_formulas=False, page_count=0,
                  encrypted=False, form_fields=False, lang='unknown',
                  chinese_ratio=0.0, file_size_mb=round(get_file_size_mb(filepath), 2),
                  sampled_pages=[], analysis_complete=False, recommended_flags=['--tables'],
                  warnings=[], error=None, error_code=None)
    if sample_pages < 1:
        result.update(error='采样页数必须大于 0。', error_code='invalid_options')
        return result
    try:
        reader = PdfReader(str(filepath))
        result['encrypted'] = bool(reader.is_encrypted)
        if reader.is_encrypted and not reader.decrypt(password or ''):
            result.update(type='encrypted', error='需要有效的 PDF 密码。',
                          error_code='password_required', recommended_flags=[])
            return result
        count = len(reader.pages)
        result['page_count'] = count
        if count == 0:
            raise ValueError('PDF 没有页面。')
        try:
            result['form_fields'] = bool(reader.get_fields())
        except Exception as exc:
            result['warnings'].append(f'表单检测未完成：{type(exc).__name__}')
        samples = min(sample_pages, count)
        indices = [0] if samples == 1 else sorted({round(i * (count - 1) / (samples - 1)) for i in range(samples)})
        result['sampled_pages'] = [i + 1 for i in indices]
        result['analysis_complete'] = len(indices) == count
        texts, records = [], []
        for index in indices:
            page = reader.pages[index]
            try:
                text = page.extract_text() or ''
                image = _contains_image(page)
                records.append((bool(text.strip()), image))
                texts.append(text)
            except Exception as exc:
                records.append((False, False))
                result['warnings'].append(f'第 {index + 1} 页检测失败：{type(exc).__name__}')
        content = '\n'.join(texts)
        zh, latin = len(RE_CHINESE.findall(content)), len(RE_LATIN.findall(content))
        result['chinese_ratio'] = round(zh / max(1, zh + latin), 3)
        if zh + latin >= 20:
            result['lang'] = 'zh' if result['chinese_ratio'] > 0.1 else 'en'
        result['has_text_layer'] = any(text for text, image in records)
        result['has_images'] = any(image for text, image in records)
        result['has_formulas'] = bool(RE_FORMULA.search(content))
        scanned = any(image and not text for text, image in records)
        if result['form_fields']:
            result['type'] = 'form'
        elif scanned and not result['has_text_layer']:
            result['type'] = 'scanned'
        elif scanned or (result['has_text_layer'] and result['has_images']):
            result['type'] = 'mixed'
        elif result['has_text_layer']:
            result['type'] = 'vector_text'
        if result['type'] == 'scanned':
            result['recommended_flags'].insert(0, '--force-ocr')
        elif (result['analysis_complete'] and all(text and not image for text, image in records)
              and not result['form_fields'] and not result['warnings']):
            result['recommended_flags'].insert(0, '--no-ocr')
        if not result['analysis_complete']:
            result['warnings'].append('未检查全部页面，保持 OCR 开启以覆盖未采样的扫描页。')
        if result['lang'] == 'unknown':
            result['warnings'].append('文本不足，语言未知；需要指定语言时使用所选 OCR 引擎的语言代码。')
        if result['has_formulas']:
            result['warnings'].append('发现公式线索；公式检测为启发式，需要时显式启用 --enrich-formula。')
    except Exception as exc:
        result.update(error=f'PDF 解析失败：{type(exc).__name__}: {exc}',
                      error_code='parse_error', recommended_flags=[])
    return result


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='单 PDF 分散采样分析')
    parser.add_argument('input')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--sample-pages', type=int, default=7)
    parser.add_argument('--pdf-password')
    args = parser.parse_args()
    try:
        result = detect_pdf_type(verify_file(args.input), args.sample_pages, args.pdf_password)
        print(format_output(result, args.json))
        return 1 if result['error'] else 0
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
