# Docling Skill for Claude Code

[English](#english) | [中文](#中文)

---

## English

### Introduction

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that integrates [Docling](https://github.com/docling-project/docling) — IBM's enterprise-grade document parsing platform — into your terminal-based AI workflow. Convert documents between formats directly through natural language commands.

### Why This Skill?

While Claude Code can read many file types natively, complex documents (academic PDFs with formulas, scanned papers, multi-column layouts, tables) require specialized parsing. Docling provides:

- **Deep PDF understanding**: Layout analysis, reading order correction, table structure recognition, formula and code block detection
- **Lightweight architecture**: ~550MB of specialized models, all local inference, zero API calls
- **Broad format support**: PDF, DOCX, PPTX, XLSX, HTML, EPUB, images, audio, video, email, LaTeX, and more
- **Multiple output formats**: Markdown, JSON (lossless), YAML, HTML, DocTags, WebVTT, plain text, RAG chunks

### Prerequisites

| Dependency | Version | Note |
|------------|---------|------|
| Python | >= 3.10 | Required by Docling |
| Claude Code | Latest | Terminal AI assistant |
| Docling | >= 2.0 | Document parsing engine |

> **The skill assumes these are already installed.** If `docling` is not found at runtime, the skill will prompt you to install it — it will NOT install automatically without your consent.

> **Mirror fallback (China mainland)**: `pip install docling -i https://pypi.tuna.tsinghua.edu.cn/simple`

### Installation

1. **Copy the skill directory** to your Claude Code skills directory:

```bash
# Linux / macOS
mkdir -p ~/.claude/skills/docling
cp SKILL.md ~/.claude/skills/docling/SKILL.md
cp -r scripts/ ~/.claude/skills/docling/scripts/

# Windows (PowerShell)
New-Item -ItemType Directory -Force $env:USERPROFILE\.claude\skills\docling
Copy-Item SKILL.md $env:USERPROFILE\.claude\skills\docling\SKILL.md
Copy-Item -Recurse scripts/ $env:USERPROFILE\.claude\skills\docling\scripts/
```

2. **Install pypdf** (required by detection scripts):

```bash
pip install pypdf -i https://pypi.tuna.tsinghua.edu.cn/simple
```

3. **Restart Claude Code** (or start a new session). The skill is auto-detected.

4. **First use**: Docling will auto-download model artifacts (~550MB) on first run. No manual setup needed.

### Usage

Invoke with `/Docling` followed by your natural language request:

```
/Docling Convert "paper.pdf" to markdown in the same directory
/Docling 将 "report.docx" 转为 HTML，输出到 ./output/
/Docling Extract text from "scanned.pdf" with OCR for Chinese
/Docling Convert "meeting.mp4" to subtitles (VTT format)
```

#### Supported Input Formats

| Category | Formats |
|----------|---------|
| Documents | PDF, DOCX, PPTX, XLSX, ODF (ODT, ODS, ODP) |
| Web / Text | HTML, EPUB, LaTeX, plain text (.txt), Markdown (.qmd, .Rmd) |
| Images | PNG, TIFF, JPEG, BMP |
| Audio / Video | WAV, MP3, MP4, AVI, MOV, MKV, WebM |
| Email | EML, MSG |
| Other | WebVTT, Box Notes, XBRL, DocLang |

#### Supported Output Formats

| Format | Flag | Use Case |
|--------|------|----------|
| Markdown | `--to md` | Default. General-purpose, LLM-friendly |
| JSON | `--to json` | Lossless. Full document structure preserved |
| YAML | `--to yaml` | Structured data, config-friendly |
| HTML | `--to html` | Web publishing |
| HTML Split Page | `--to html_split_page` | Per-page HTML files |
| Plain Text | `--to text` | Minimal, text-only extraction |
| DocTags | `--to doctags` | Structured document tags |
| WebVTT | `--to vtt` | Subtitles for audio/video |
| DocLang | `--to doclang` | DocLang format |
| Chunks | `--to chunks` | RAG pipeline preparation |

### How It Works

```
User: /Docling Convert "thesis.pdf" to markdown
         │
         ▼
┌─────────────────────────────┐
│  Claude Code reads SKILL.md │
│  Parses user intent         │
│  Selects appropriate flags  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Executes:                  │
│  docling thesis.pdf --to md │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Docling Pipeline:          │
│  1. PDF parsing             │
│  2. Layout analysis (164MB) │
│  3. Table structure (342MB) │
│  4. OCR (RapidOCR)          │
│  5. Reading order            │
│  6. Heading hierarchy        │
│  7. Export to Markdown       │
└─────────────┬───────────────┘
              │
              ▼
       thesis.md generated
```

### Scripts

The skill includes pre-built Python scripts for common operations:

```
scripts/
├── detect_pdf_type.py      # PDF deep analysis (type/language/recommended flags)
├── convert_single.py       # Single file converter (pure executor, no auto-detection)
├── convert_batch.py        # Batch sequential conversion
└── utils.py                # Shared utilities
```

#### `detect_pdf_type.py` — PDF Deep Analysis

Analyzes PDF structure before conversion to select optimal parameters.

```bash
# Plain text output
python scripts/detect_pdf_type.py input.pdf

# JSON output
python scripts/detect_pdf_type.py input.pdf --json
```

Output fields:

| Field | Description |
|-------|-------------|
| `type` | vector_text / scanned / mixed / academic / form / encrypted / unknown |
| `has_text_layer` | Whether extractable text exists |
| `has_images` | Whether images are present |
| `has_formulas` | Whether LaTeX formulas detected |
| `page_count` | Total pages |
| `encrypted` | Whether PDF is encrypted |
| `form_fields` | Whether form fields exist |
| `lang` | zh / en |
| `lang_confidence` | Chinese character ratio (0-1) |
| `recommended_flags` | Suggested docling CLI flags |

#### `convert_single.py` — Single File Converter

Pure executor: receives parameters, runs docling, returns result. No auto-detection.

```bash
python scripts/convert_single.py input.pdf --to md --output ./out/
python scripts/convert_single.py input.pdf --to json --no-ocr --tables
```

#### `convert_batch.py` — Batch Sequential Converter

Converts all matching files in a directory sequentially. Parallel execution is handled by Claude Code Agent.

```bash
python scripts/convert_batch.py ./docs/ --to md --output ./out/
python scripts/convert_batch.py ./docs/ --to md --output ./out/ --ext pdf,docx
```

### PDF Analysis Workflow

When you invoke `/Docling` with a PDF file, the skill automatically:

1. **Detects PDF type** (vector/scanned/mixed/academic/form/encrypted)
2. **Identifies language** (Chinese/English) by sampling text
3. **Recommends optimal flags** based on analysis
4. **Executes conversion** with the right parameters

```
User: /Docling Convert "paper.pdf" to markdown
         │
         ▼
┌─────────────────────────────────┐
│  detect_pdf_type.py analyzes    │
│  → type: vector_text            │
│  → lang: en                     │
│  → recommended: --no-ocr        │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  convert_single.py executes     │
│  docling paper.pdf --to md      │
│  --no-ocr --tables              │
└─────────────┬───────────────────┘
              │
              ▼
       paper.md generated
```

### Format Analysis Coverage

| Format | Analysis Level | Details |
|--------|---------------|---------|
| **PDF** | **Full depth** | Detects vector text, scanned, mixed, academic, form, encrypted. Identifies language (zh/en). Auto-selects optimal conversion parameters. |
| **DOCX, PPTX, HTML, images, audio, video, etc.** | **Basic** | Supported for conversion, but no pre-conversion analysis. Uses default parameters. User may manually specify flags. |

> This skill is currently **PDF expert level**. Other formats work well with default settings but lack intelligent pre-analysis. Contributions welcome.

### Advanced Options

#### PDF Processing

```bash
# Disable OCR (for clean vector PDFs)
docling input.pdf --no-ocr

# Force OCR on all content
docling input.pdf --force-ocr

# VLM pipeline for complex layouts
docling input.pdf --pipeline vlm --vlm-model granite_docling

# Formula enrichment
docling input.pdf --enrich-formula

# Code block enrichment
docling input.pdf --enrich-code

# Chart data extraction
docling input.pdf --enrich-chart-data

# Password-protected PDF
docling encrypted.pdf --pdf-password mypassword
```

#### OCR Language

```bash
# Chinese + English OCR
docling input.pdf --ocr-lang zh,en

# Use specific OCR engine
docling input.pdf --ocr-engine tesseract
```

#### Audio / Video

```bash
# Transcribe audio with Whisper
docling audio.mp3 --pipeline asr --asr-model whisper_medium

# Video with speaker diarization
docling video.mp4 --video-diarization
```

#### Batch Processing

When converting multiple files, the skill presents three execution strategies:

| Strategy | Description | Best For |
|----------|-------------|----------|
| **Sequential** | One file at a time, single script | < 10 files, precise control, unified log |
| **Parallel Agents** | Multiple files concurrently via Claude Code agents | >= 10 files, no inter-file dependencies, maximum speed |
| **Custom Batching** | User-defined groups, each group uses sequential or parallel | Mixed formats, large files need isolation, or custom logic |

The skill will ask you to choose when it detects multiple input files:

```
检测到批量转换任务（15 个文件），请选择执行策略：

A. 顺序执行（单脚本）— 逐个转换，稳定可靠
B. 并行执行（多 Agent）— 同时处理，速度最快
C. 自定义分批 — 按你的规则分组执行
```

```bash
# You can also use Docling's built-in directory conversion:
docling ./documents/ --to md --output ./converted/

# Or convert from URL:
docling https://arxiv.org/pdf/2206.01062
```

### Architecture Notes

Docling does **NOT** use large language models. Its pipeline consists of:

| Component | Model | Size | Purpose |
|-----------|-------|------|---------|
| Layout Analysis | docling-layout-heron | 164 MB | Detect text blocks, tables, figures, headers |
| Table Structure | docling-models | 342 MB | Recognize rows, columns, cells |
| OCR | RapidOCR (PP-OCRv6) | ~50 MB | Text extraction from images/scans |
| Reading Order | Rule-based + lightweight | - | Determine logical reading sequence |
| Heading Hierarchy | Rule-based + lightweight | - | Detect H1/H2/H3 levels |

**Total: ~550MB, all local, zero API calls.**

First run downloads models from HuggingFace. Subsequent runs use local cache.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `docling: command not found` | Skill will prompt to install. Or manually: `pip install docling -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| HuggingFace symlink warning (Windows) | Cosmetic only. Set `HF_HUB_DISABLE_SYMLINKS_WARNING=1` to suppress |
| Slow conversion | First run downloads ~550MB models. After caching, vector PDFs convert in seconds |
| OCR quality poor | Try `--force-ocr` or `--ocr-engine tesseract` for different results |
| Memory errors on large PDFs | Process in smaller batches, or use `--no-tables` to reduce memory usage |
| Want parallel batch conversion | Specify multiple files when invoking `/Docling` — the skill offers sequential, parallel agent, or custom strategies |
| Chinese filename PDF fails on Windows | Docling bug: temp file permission error with CJK paths. Workaround: rename file to ASCII-only name before converting |

### Known Limitations

- **Docling + Windows + Chinese paths**: Docling has a known issue with temporary file handling when file paths contain CJK characters. Conversion may fail with `PermissionError`. Workaround: rename files to ASCII-only names before converting.
- **Form PDF language detection**: Form-type PDFs without text layers default to `lang: en`. If the document is actually Chinese, the skill will still work but may not add `--ocr-lang zh,en` automatically.
- **Formula detection**: Uses regex matching for LaTeX patterns. May miss formulas in non-LaTeX formats (e.g., images of equations).

### License

MIT License. See [LICENSE](LICENSE) for details.

### Acknowledgments

- [Docling](https://github.com/docling-project/docling) by IBM Research
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) by Anthropic

---

## 中文

### 简介

一个 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 技能，将 [Docling](https://github.com/docling-project/docling)（IBM 企业级文档解析平台）集成到终端 AI 工作流中。通过自然语言指令直接完成文档格式转换。

### 为什么需要这个技能？

Claude Code 原生支持读取多种文件类型，但复杂文档（含公式的学术论文、扫描件、多栏排版、表格）需要专业解析工具。Docling 提供：

- **深度 PDF 理解**：版面分析、阅读顺序校正、表格结构识别、公式与代码块检测
- **轻量架构**：~550MB 专用模型，全部本地推理，零 API 调用
- **广泛格式支持**：PDF、DOCX、PPTX、XLSX、HTML、EPUB、图片、音频、视频、邮件、LaTeX 等
- **多种输出格式**：Markdown、JSON（无损）、YAML、HTML、DocTags、WebVTT、纯文本、RAG 分块

### 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | >= 3.10 | Docling 运行依赖 |
| Claude Code | 最新版 | 终端 AI 助手 |
| Docling | >= 2.0 | 文档解析引擎 |

> **技能默认假设这些已安装。** 若运行时未检测到 `docling`，会提示你是否安装 — 不会在未经同意的情况下自动安装。

> **国内镜像兜底**：`pip install docling -i https://pypi.tuna.tsinghua.edu.cn/simple`

### 安装步骤

1. **复制技能目录**到 Claude Code 技能目录：

```bash
# Linux / macOS
mkdir -p ~/.claude/skills/docling
cp SKILL.md ~/.claude/skills/docling/SKILL.md
cp -r scripts/ ~/.claude/skills/docling/scripts/

# Windows (PowerShell)
New-Item -ItemType Directory -Force $env:USERPROFILE\.claude\skills\docling
Copy-Item SKILL.md $env:USERPROFILE\.claude\skills\docling\SKILL.md
Copy-Item -Recurse scripts/ $env:USERPROFILE\.claude\skills\docling\scripts\
```

2. **安装 pypdf**（检测脚本依赖）：

```bash
pip install pypdf -i https://pypi.tuna.tsinghua.edu.cn/simple
```

3. **重启 Claude Code**（或开启新会话），技能自动加载。

4. **首次使用**：Docling 会在首次运行时自动下载模型文件（~550MB），无需手动配置。

### 使用方式

通过 `/Docling` 加自然语言指令调用：

```
/Docling 将 "paper.pdf" 转换为 markdown，生成在同目录下
/Docling Convert "report.docx" to HTML, output to ./output/
/Docling 提取 "scanned.pdf" 的文字，启用中文 OCR
/Docling 将 "meeting.mp4" 转为字幕（VTT 格式）
```

#### 支持的输入格式

| 类别 | 格式 |
|------|------|
| 文档 | PDF、DOCX、PPTX、XLSX、ODF（ODT、ODS、ODP） |
| 网页/文本 | HTML、EPUB、LaTeX、纯文本 (.txt)、Markdown (.qmd, .Rmd) |
| 图片 | PNG、TIFF、JPEG、BMP |
| 音视频 | WAV、MP3、MP4、AVI、MOV、MKV、WebM |
| 邮件 | EML、MSG |
| 其他 | WebVTT、Box Notes、XBRL、DocLang |

#### 支持的输出格式

| 格式 | 参数 | 适用场景 |
|------|------|----------|
| Markdown | `--to md` | 默认。通用，LLM 友好 |
| JSON | `--to json` | 无损。保留完整文档结构 |
| YAML | `--to yaml` | 结构化数据，配置友好 |
| HTML | `--to html` | 网页发布 |
| HTML 分页 | `--to html_split_page` | 每页独立 HTML 文件 |
| 纯文本 | `--to text` | 最简，仅提取文字 |
| DocTags | `--to doctags` | 结构化文档标签 |
| WebVTT | `--to vtt` | 音视频字幕 |
| DocLang | `--to doclang` | DocLang 格式 |
| Chunks | `--to chunks` | RAG 管线预处理 |

### 工作流程

```
用户: /Docling 将 "thesis.pdf" 转换为 markdown
         │
         ▼
┌─────────────────────────────┐
│  Claude Code 读取 SKILL.md  │
│  解析用户意图               │
│  选择合适的参数             │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  执行命令:                  │
│  docling thesis.pdf --to md │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Docling 处理管线:          │
│  1. PDF 解析                │
│  2. 版面分析 (164MB)        │
│  3. 表格结构识别 (342MB)    │
│  4. OCR (RapidOCR)          │
│  5. 阅读顺序重排            │
│  6. 标题层级识别            │
│  7. 导出为 Markdown         │
└─────────────┬───────────────┘
              │
              ▼
       生成 thesis.md
```

### 预存脚本

技能内置 Python 脚本，覆盖常见操作场景，避免重复造轮子：

```
scripts/
├── detect_pdf_type.py      # PDF 深度分析（类型/语言/推荐参数）
├── convert_single.py       # 单文件转换（纯执行器）
├── convert_batch.py        # 批量顺序转换
└── utils.py                # 共用工具函数
```

#### `detect_pdf_type.py` — PDF 深度分析

在转换前分析 PDF 结构，自动选择最优参数。

```bash
# 纯文本输出
python scripts/detect_pdf_type.py input.pdf

# JSON 输出
python scripts/detect_pdf_type.py input.pdf --json
```

输出字段：

| 字段 | 说明 |
|------|------|
| `type` | vector_text / scanned / mixed / academic / form / encrypted / unknown |
| `has_text_layer` | 是否有可提取的文本层 |
| `has_images` | 是否包含图片 |
| `has_formulas` | 是否包含 LaTeX 公式 |
| `page_count` | 总页数 |
| `encrypted` | 是否加密 |
| `form_fields` | 是否包含表单字段 |
| `lang` | zh / en |
| `lang_confidence` | 中文字符占比（0-1） |
| `recommended_flags` | 推荐的 docling CLI 参数 |

#### `convert_single.py` — 单文件转换

纯执行器：接收参数，调用 docling，返回结果。不做自动检测。

```bash
python scripts/convert_single.py input.pdf --to md --output ./out/
python scripts/convert_single.py input.pdf --to json --no-ocr --tables
```

#### `convert_batch.py` — 批量顺序转换

遍历目录，按扩展名过滤，顺序执行转换。并行由 SKILL.md 调度 Agent 实现。

```bash
python scripts/convert_batch.py ./docs/ --to md --output ./out/
python scripts/convert_batch.py ./docs/ --to md --output ./out/ --ext pdf,docx
```

### PDF 分析工作流

使用 `/Docling` 处理 PDF 时，技能会自动：

1. **检测 PDF 类型**（矢量/扫描/混合/学术/表单/加密）
2. **识别语言**（中文/英文）通过采样文本
3. **推荐最优参数**基于分析结果
4. **执行转换**使用正确的参数

```
用户: /Docling 将 "paper.pdf" 转为 markdown
         │
         ▼
┌─────────────────────────────────┐
│  detect_pdf_type.py 分析        │
│  → type: vector_text            │
│  → lang: en                     │
│  → recommended: --no-ocr        │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  convert_single.py 执行         │
│  docling paper.pdf --to md      │
│  --no-ocr --tables              │
└─────────────┬───────────────────┘
              │
              ▼
       生成 paper.md
```

### 格式分析覆盖范围

| 格式 | 分析深度 | 说明 |
|------|---------|------|
| **PDF** | **专家级** | 检测矢量文字、扫描件、混合型、学术论文、表单、加密。识别中英文。自动选择最优转换参数。 |
| **DOCX、PPTX、HTML、图片、音视频等** | **基础** | 支持转换，但无预分析。使用默认参数。用户可手动指定参数。 |

> 本技能目前**对 PDF 达到专家级**。其他格式使用默认参数即可正常转换，但缺少智能预分析。欢迎贡献。

### 高级选项

#### PDF 处理

```bash
# 禁用 OCR（适用于纯矢量 PDF）
docling input.pdf --no-ocr

# 强制对所有内容执行 OCR
docling input.pdf --force-ocr

# 使用 VLM 管线处理复杂版面
docling input.pdf --pipeline vlm --vlm-model granite_docling

# 公式识别增强
docling input.pdf --enrich-formula

# 代码块识别增强
docling input.pdf --enrich-code

# 图表数据提取
docling input.pdf --enrich-chart-data

# 加密 PDF
docling encrypted.pdf --pdf-password mypassword
```

#### OCR 语言设置

```bash
# 中英文混合 OCR
docling input.pdf --ocr-lang zh,en

# 指定 OCR 引擎
docling input.pdf --ocr-engine tesseract
```

#### 音视频处理

```bash
# 使用 Whisper 转录音频
docling audio.mp3 --pipeline asr --asr-model whisper_medium

# 视频 + 说话人分离
docling video.mp4 --video-diarization
```

#### 批量处理

转换多个文件时，技能会提供三种执行策略供选择：

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| **顺序执行** | 单脚本逐个转换 | 文件少（<10）、需要精确控制、统一日志 |
| **并行执行** | 多 Agent 同时处理 | 文件多（>=10）、文件间无依赖、追求速度 |
| **自定义分批** | 用户指定分组方式和每组策略 | 混合格式、大文件需隔离、或有特殊逻辑 |

当检测到多个输入文件时，技能会询问：

```
检测到批量转换任务（15 个文件），请选择执行策略：

A. 顺序执行（单脚本）— 逐个转换，稳定可靠
B. 并行执行（多 Agent）— 同时处理，速度最快
C. 自定义分批 — 按你的规则分组执行
```

```bash
# 也可以直接使用 Docling 内置的目录转换：
docling ./documents/ --to md --output ./converted/

# 或从 URL 转换：
docling https://arxiv.org/pdf/2206.01062
```

### 架构说明

Docling **不使用大语言模型**。其管线由以下组件构成：

| 组件 | 模型 | 大小 | 功能 |
|------|------|------|------|
| 版面分析 | docling-layout-heron | 164 MB | 检测文本块、表格、图片、标题区域 |
| 表格结构 | docling-models | 342 MB | 识别行、列、单元格 |
| OCR | RapidOCR (PP-OCRv6) | ~50 MB | 从图片/扫描件提取文字 |
| 阅读顺序 | 规则 + 轻量模型 | - | 确定逻辑阅读顺序 |
| 标题层级 | 规则 + 轻量模型 | - | 识别 H1/H2/H3 层级 |

**总计约 550MB，全部本地推理，零 API 调用。**

首次运行从 HuggingFace 下载模型，后续使用本地缓存。

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| `docling: command not found` | 技能会提示是否安装。也可手动：`pip install docling -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| HuggingFace symlink 警告（Windows） | 仅影响显示。设置 `HF_HUB_DISABLE_SYMLINKS_WARNING=1` 抑制 |
| 转换速度慢 | 首次运行需下载 ~550MB 模型。缓存后矢量 PDF 秒级完成 |
| OCR 效果差 | 尝试 `--force-ocr` 或 `--ocr-engine tesseract` |
| 大文件内存不足 | 分批处理，或使用 `--no-tables` 减少内存占用 |
| 批量转换想并行 | 触发 `/Docling` 时说明多个文件，技能会提供顺序/并行/自定义三种策略 |
| Windows 中文文件名 PDF 失败 | Docling 已知 bug：中文路径临时文件权限错误。解决：将文件重命名为纯英文后再转换 |

### 已知限制

- **Docling + Windows + 中文路径**：Docling 在处理包含中文字符的文件路径时，临时文件清理会报 `PermissionError`。解决：将文件重命名为纯英文。
- **表单 PDF 语言检测**：无文本层的表单 PDF 默认返回 `lang: en`。如果实际是中文文档，技能仍可工作，但可能不会自动加 `--ocr-lang zh,en`。
- **公式检测**：使用正则匹配 LaTeX 模式，可能遗漏非 LaTeX 格式的公式（如图片中的公式）。

### 许可证

MIT License。详见 [LICENSE](LICENSE)。

### 致谢

- [Docling](https://github.com/docling-project/docling) — IBM Research
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — Anthropic
