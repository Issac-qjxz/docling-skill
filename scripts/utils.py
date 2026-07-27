"""
Docling Skill - 共用工具函数
路径处理、日志格式化、文件验证等。
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional


def verify_file(filepath: str) -> Path:
    """验证文件存在且可读，返回 Path 对象。不存在则打印错误并退出。"""
    p = Path(filepath)
    if not p.exists():
        print(f"ERROR: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    if not p.is_file():
        print(f"ERROR: Not a file: {filepath}", file=sys.stderr)
        sys.exit(1)
    return p


def verify_dir(dirpath: str) -> Path:
    """验证目录存在，不存在则创建。"""
    p = Path(dirpath)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_file_size_mb(filepath: Path) -> float:
    """获取文件大小（MB）。"""
    return filepath.stat().st_size / (1024 * 1024)


def format_output(data: dict, as_json: bool = False) -> str:
    """格式化输出：默认纯文本，--json 输出 JSON。"""
    if as_json:
        return json.dumps(data, indent=2, ensure_ascii=False)
    lines = []
    for key, value in data.items():
        if isinstance(value, list):
            value = " ".join(str(v) for v in value)
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def print_result(filepath: str, success: bool, elapsed: float,
                 output_path: Optional[str] = None, error: Optional[str] = None):
    """打印单文件转换结果。"""
    status = "OK" if success else "FAILED"
    msg = f"[{status}] {filepath} ({elapsed:.1f}s)"
    if output_path:
        msg += f" → {output_path}"
    if error:
        msg += f" | {error}"
    print(msg)


def print_summary(total: int, success: int, failed: int, total_time: float):
    """打印批量转换汇总。"""
    print(f"\nSummary: {success}/{total} succeeded, {failed} failed ({total_time:.1f}s total)")


def is_pdf(filepath: Path) -> bool:
    """判断文件是否为 PDF（基于扩展名）。"""
    return filepath.suffix.lower() == ".pdf"
