"""单 PDF 输入验证与结果格式化；不包含随机操作。"""
import json
from pathlib import Path


def verify_file(filepath: str) -> Path:
    if str(filepath).lower().startswith(('http://', 'https://')):
        raise ValueError('仅接收本地 PDF；请先下载 URL 指向的文件。')
    path = Path(filepath).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f'PDF 文件不存在或不是文件：{path}')
    if path.suffix.lower() != '.pdf':
        raise ValueError('仅支持单个 .pdf 文件。')
    with path.open('rb') as stream:
        if b'%PDF-' not in stream.read(1024):
            raise ValueError('文件内容不是 PDF，或 PDF 文件头损坏。')
    return path


def verify_dir(dirpath: str) -> Path:
    """仅用于输出目录；输入目录从不创建。"""
    path = Path(dirpath).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size_mb(filepath: Path) -> float:
    return filepath.stat().st_size / (1024 * 1024)


def format_output(data: dict, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(data, indent=2, ensure_ascii=False)
    return '\n'.join(f'{key}: {value}' for key, value in data.items())
