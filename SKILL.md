---
name: docling
description: Use this skill when the user wants to convert documents using Docling. Supports converting PDF, DOCX, PPTX, XLSX, HTML, EPUB, images, audio, video, email, LaTeX, and more to Markdown, JSON, HTML, YAML, DocTags, WebVTT, DocLang, or plain text. Trigger on /Docling or when user mentions docling document conversion.
---

# Docling Document Conversion

## Overview

Docling is an enterprise-grade document parsing platform (IBM) with deep PDF understanding capabilities. Use the `docling` CLI to convert documents.

**Architecture**: Docling uses multiple small specialized models (~550MB total), NOT large language models. Components: layout analysis (164MB), table structure recognition (342MB), OCR (RapidOCR), reading order model, heading hierarchy model. All inference is local, zero API calls.

## Supported Formats

### Input Formats
| Category | Formats |
|----------|---------|
| Documents | PDF, DOCX, PPTX, XLSX, ODF (ODT, ODS, ODP) |
| Web/Text | HTML, EPUB, LaTeX, plain text (.txt), Markdown (.qmd, .Rmd) |
| Images | PNG, TIFF, JPEG, BMP |
| Audio/Video | WAV, MP3, MP4, AVI, MOV, MKV, WebM |
| Email | EML, MSG |
| Other | WebVTT, Box Notes, XBRL, DocLang |

### Output Formats
| Format | Flag | Description |
|--------|------|-------------|
| Markdown | `--to md` | Default. Structured Markdown with headings, tables, lists |
| JSON | `--to json` | Lossless JSON representation (DoclingDocument) |
| YAML | `--to yaml` | YAML representation |
| HTML | `--to html` | Full HTML output |
| HTML Split Page | `--to html_split_page` | One HTML file per page |
| Plain Text | `--to text` | Plain text only |
| DocTags | `--to doctags` | Structured document tags |
| WebVTT | `--to vtt` | Subtitle format (for audio/video) |
| DocLang | `--to doclang` | DocLang format |
| Chunks | `--to chunks` | Chunked output for RAG pipelines |

## Scripts

All scripts are in `scripts/` relative to this SKILL.md. Use the full path when calling them.

```
scripts/
├── detect_pdf_type.py      # PDF 深度分析（类型/语言/推荐参数）
├── convert_single.py       # 单文件转换（纯执行器）
├── convert_batch.py        # 批量顺序转换
└── utils.py                # 共用工具函数
```

### Script: `detect_pdf_type.py`

分析 PDF 文件类型、语言、结构特征，输出推荐转换参数。

```bash
# 纯文本输出
python scripts/detect_pdf_type.py input.pdf

# JSON 输出
python scripts/detect_pdf_type.py input.pdf --json

# 采样更多页（默认 3 页）
python scripts/detect_pdf_type.py input.pdf --sample-pages 5
```

**输出字段**：
| 字段 | 说明 |
|------|------|
| `type` | vector_text / scanned / mixed / academic / form / encrypted / unknown |
| `has_text_layer` | 是否有可提取的文本层 |
| `has_images` | 是否包含图片 |
| `has_formulas` | 是否包含公式（LaTeX 特征） |
| `page_count` | 总页数 |
| `encrypted` | 是否加密 |
| `form_fields` | 是否包含表单字段 |
| `lang` | zh / en |
| `lang_confidence` | 中文字符占比（0-1） |
| `recommended_flags` | 推荐的 docling CLI 参数 |

**类型判定逻辑**：
```
encrypted → form → scanned → academic → mixed → vector_text → unknown
```

### Script: `convert_single.py`

纯转换器，不做自动检测。参数由调用者决定。

```bash
python scripts/convert_single.py input.pdf --to md --output ./out/
python scripts/convert_single.py input.pdf --to json --no-ocr --tables
python scripts/convert_single.py input.pdf --to md --force-ocr --ocr-lang zh,en
```

### Script: `convert_batch.py`

批量顺序转换目录下的文件。并行由 SKILL.md 调度 Agent 实现。

```bash
python scripts/convert_batch.py ./docs/ --to md --output ./out/
python scripts/convert_batch.py ./docs/ --to md --output ./out/ --ext pdf,docx
```

## Workflow

When the user invokes `/Docling`:

### Step 0: Environment Check

**Default assumption**: User already has Python and Docling installed. Do NOT check proactively.

Only act if the `docling` command actually fails at execution. If it does:

1. Inform the user that Docling is not installed or not in PATH.
2. Ask: "是否安装 Docling？（pip install docling）" — do NOT install without consent.
3. If user agrees, install with mirror fallback: `pip install docling -i https://pypi.tuna.tsinghua.edu.cn/simple`
4. If user declines, stop and explain that Docling is required for this skill.

### Step 1: Identify Input & Output

1. Ask the user for the input file path(s) or URL(s).
2. Verify the file exists. If not found, report and stop.
3. Determine output format from user's description. Default to Markdown if unspecified.
4. Determine output directory. Default to same directory as input file.

### Step 1.5: File Analysis (PDF only)

**For PDF files**: Run `detect_pdf_type.py` to analyze the file before converting.

```bash
python scripts/detect_pdf_type.py "input.pdf" --json
```

Parse the JSON output to get:
- `type`: Determines base conversion strategy
- `lang`: Determines whether to add `--ocr-lang`
- `recommended_flags`: Base flags to pass to converter
- `encrypted`: If true, ask user for password before proceeding

**For non-PDF files**: Skip analysis. Use default parameters. No pre-conversion detection is implemented for other formats yet.

### Step 2: Parameter Decision

Based on `detect_pdf_type.py` output (for PDF) or user description (for other formats):

**PDF parameter mapping** (from script output):
| type | recommended_flags |
|------|-------------------|
| vector_text | `--no-ocr --tables` |
| scanned | `--force-ocr --tables` |
| mixed | `--tables` |
| academic | `--tables --enrich-formula` |
| form (has text) | `--tables` |
| form (no text) | `--force-ocr --tables` |
| encrypted | `--pdf-password <ask user>` |
| unknown | `--tables` |

**Language override**:
- If `lang == zh` AND type is `scanned` or `mixed` → add `--ocr-lang zh,en`
- Otherwise → no language flag needed

**User overrides**: If the user explicitly specifies flags (e.g., "强制 OCR"), those override the script's recommendations.

### Step 3: Execute

**Single file**: Call `convert_single.py` with the determined parameters.

```bash
python scripts/convert_single.py "input.pdf" --to md --output "./out/" <recommended_flags>
```

**Multiple files or directory**: Present execution strategies via `AskUserQuestion`:

```
检测到批量转换任务（N 个文件），请选择执行策略：

A. 顺序执行（单脚本）
   - 一个接一个转换，稳定可靠
   - 适合文件较少（<10）或需要精确控制的场景
   - 输出统一日志

B. 并行执行（多 Agent）
   - 每个文件分配一个独立 Agent 并行处理
   - 适合文件较多（>=10）且文件间无依赖的场景
   - 速度最快，但日志分散

C. 自定义分批
   - 你来指定分几批、每批哪些文件
   - 适合需要按类别/格式分组处理的场景
   - 例如：PDF 一批、DOCX 一批，或大文件单独跑
```

**Strategy A**: Call `convert_batch.py`:
```bash
python scripts/convert_batch.py "./docs/" --to md --output "./out/" --ext pdf
```

**Strategy B**: Use Agent tool to spawn parallel agents, each running `convert_single.py` on a subset of files.

**Strategy C**: Ask user for grouping rules, then execute each group with A or B.

### Step 4: Report Results

After conversion, report:
- Output file path(s)
- File size(s)
- Conversion time
- For PDF: detected type, language, and flags used
- Any warnings or errors encountered
- For batch: success/failure summary table

## Decision Logic

- **Standard vector PDF** → `--no-ocr --tables`
- **Scanned PDF** → `--force-ocr --tables` + `--ocr-lang zh,en` if Chinese
- **Academic PDF with formulas** → `--tables --enrich-formula`
- **Mixed PDF (text + images)** → `--tables` + `--ocr-lang zh,en` if Chinese
- **Form PDF** → `--no-ocr --tables`
- **Encrypted PDF** → ask user for password, then retry
- **Audio/Video** → `--pipeline asr`
- **RAG pipeline prep** → `--to chunks` or `--to json`
- **Need full fidelity** → `--to json`
- **Simple text extraction** → `--to text`
- **Other formats** → default parameters (no analysis available)

## Python API (for programmatic use)

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("input.pdf")

# Export to Markdown
md_content = result.document.export_to_markdown()
print(md_content)

# Export to JSON (lossless)
json_content = result.document.export_to_json("output.json")
```

## Format Analysis Coverage

- **PDF**: Full depth analysis — detects vector text, scanned, mixed, academic, form, encrypted. Identifies language (zh/en). Automatically selects optimal conversion parameters.
- **Other formats (DOCX, PPTX, HTML, images, audio, video, etc.)**: Supported for conversion, but no pre-conversion analysis. Uses default parameters. User may manually specify flags if needed.

## Notes

- **First run**: Will download model artifacts (~550MB total) from HuggingFace. Subsequent runs use cache.
- **Default OCR engine**: RapidOCR (PP-OCRv6, ONNX Runtime). Also available: `tesseract`, `easyocr`.
- **Default behavior**: OCR is ON, table structure extraction is ON. Use `--no-ocr` / `--no-tables` to disable.
- **Performance**: Standard vector PDFs convert in seconds. Scanned PDFs with OCR may take minutes depending on page count.
- **Windows note**: You may see HuggingFace symlink warnings. These are cosmetic — caching still works. To suppress, set `HF_HUB_DISABLE_SYMLINKS_WARNING=1`.
- **Python**: Requires 3.10+. Works on Windows, Linux, macOS (x86_64 and arm64).
