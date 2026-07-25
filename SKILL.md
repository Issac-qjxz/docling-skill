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

## CLI Usage

### Basic Conversion

```bash
# Convert to Markdown (default), output to current directory
docling input.pdf

# Convert to specific format
docling input.pdf --to json

# Specify output directory (file goes directly into this directory)
docling input.pdf --to md --output ./converted/

# Specify input format explicitly (useful for ambiguous file types)
docling input.docx --from docx --to md
```

### Output Directory Behavior

- `--output DIR`: The converted file is saved directly as `DIR/filename.ext` (no subdirectory created).
- Without `--output`: Output goes to the current working directory.
- The output filename matches the input filename with the new extension.

### PDF-Specific Options

```bash
# OCR is ENABLED by default. Disable it for pure vector PDFs:
docling input.pdf --no-ocr

# Force OCR on ALL content (replace existing text with OCR text):
docling input.pdf --force-ocr

# Use VLM pipeline for complex layouts (uses vision-language model):
docling input.pdf --pipeline vlm --vlm-model granite_docling

# Table structure extraction is ENABLED by default. Disable it:
docling input.pdf --no-tables

# Use fast table mode (less accurate but faster):
docling input.pdf --table-mode fast

# Enable formula enrichment (disabled by default):
docling input.pdf --enrich-formula

# Enable code block enrichment (disabled by default):
docling input.pdf --enrich-code

# Enable chart data extraction (disabled by default):
docling input.pdf --enrich-chart-data

# Password-protected PDF:
docling encrypted.pdf --pdf-password mypassword
```

### OCR Options

```bash
# OCR is ON by default with RapidOCR engine.
# Specify OCR language (comma-separated):
docling input.pdf --ocr-lang zh,en

# Use a specific OCR engine:
docling input.pdf --ocr-engine tesseract
docling input.pdf --ocr-engine easyocr
```

### Audio/Video Options

```bash
# Use specific ASR model for audio:
docling audio.mp3 --pipeline asr --asr-model whisper_medium

# Video with speaker diarization:
docling video.mp4 --video-diarization
```

### Multiple Files

```bash
# Convert all files in a directory:
docling ./documents/ --to md --output ./converted/

# Convert from URL:
docling https://arxiv.org/pdf/2206.01062
```

## Workflow

When the user invokes `/Docling`:

1. **Identify the input file(s)**: Ask the user for the file path(s) or URL(s). Use `ls` or `Test-Path` to verify file exists.
2. **Determine output format**: Based on user's description, select the appropriate `--to` flag. Default to Markdown if unspecified.
3. **Determine special options**: Based on document type:
   - Scanned PDF → OCR is already on by default; use `--force-ocr` only if text layer is bad
   - Academic paper with formulas → add `--enrich-formula`
   - Document with code → add `--enrich-code`
   - Chart-heavy → add `--enrich-chart-data`
   - Audio/Video → `--pipeline asr`
   - RAG prep → `--to chunks` or `--to json`
4. **Execute conversion**: Run the `docling` command with appropriate flags.
5. **Report results**: Show output file path, size, and conversion time.

## Decision Logic

- **Standard vector PDF** → default settings (OCR on, tables on, no enrichment needed)
- **Scanned PDF / image-heavy PDF** → default OCR handles it; use `--force-ocr` if the text layer from the scan is poor
- **Complex academic paper with formulas** → add `--enrich-formula`
- **Document with code blocks** → add `--enrich-code`
- **Document with charts** → add `--enrich-chart-data`
- **Audio/Video file** → use `--pipeline asr`
- **RAG pipeline preparation** → use `--to chunks` or `--to json`
- **Need full fidelity / lossless** → use `--to json`
- **Simple text extraction** → use `--to text`
- **Subtitle generation** → use `--to vtt`
- **Chinese or non-English docs** → add `--ocr-lang zh` (or relevant language code)

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

## Notes

- **First run**: Will download model artifacts (~550MB total) from HuggingFace. Subsequent runs use cache.
- **Default OCR engine**: RapidOCR (PP-OCRv6, ONNX Runtime). Also available: `tesseract`, `easyocr`.
- **Default behavior**: OCR is ON, table structure extraction is ON. Use `--no-ocr` / `--no-tables` to disable.
- **Performance**: Standard vector PDFs convert in seconds. Scanned PDFs with OCR may take minutes depending on page count.
- **Windows note**: You may see HuggingFace symlink warnings. These are cosmetic — caching still works. To suppress, set `HF_HUB_DISABLE_SYMLINKS_WARNING=1`.
- **Python**: Requires 3.10+. Works on Windows, Linux, macOS (x86_64 and arm64).
