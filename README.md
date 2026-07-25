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

| Dependency | Version | Installation |
|------------|---------|--------------|
| Python | >= 3.10 | [python.org](https://www.python.org/downloads/) |
| Claude Code | Latest | `npm install -g @anthropic-ai/claude-code` |
| Docling | >= 2.0 | `pip install docling` |

> **Mirror fallback (China mainland)**: `pip install docling -i https://pypi.tuna.tsinghua.edu.cn/simple`

### Installation

1. **Install Docling**:

```bash
pip install docling
```

2. **Copy the skill file** to your Claude Code skills directory:

```bash
# Linux / macOS
cp SKILL.md ~/.claude/skills/docling/SKILL.md

# Windows (PowerShell)
Copy-Item SKILL.md $env:USERPROFILE\.claude\skills\docling\SKILL.md
```

3. **Restart Claude Code** (or start a new session). The skill is auto-detected.

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

```bash
# Convert entire directory
docling ./documents/ --to md --output ./converted/

# Convert from URL
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
| `docling: command not found` | Ensure Python Scripts dir is in PATH, or use `python -m docling` |
| HuggingFace symlink warning (Windows) | Cosmetic only. Set `HF_HUB_DISABLE_SYMLINKS_WARNING=1` to suppress |
| Slow conversion | First run downloads ~550MB models. After caching, vector PDFs convert in seconds |
| OCR quality poor | Try `--force-ocr` or `--ocr-engine tesseract` for different results |
| Memory errors on large PDFs | Process in smaller batches, or use `--no-tables` to reduce memory usage |

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

| 依赖 | 版本 | 安装方式 |
|------|------|----------|
| Python | >= 3.10 | [python.org](https://www.python.org/downloads/) |
| Claude Code | 最新版 | `npm install -g @anthropic-ai/claude-code` |
| Docling | >= 2.0 | `pip install docling` |

> **国内镜像兜底**：`pip install docling -i https://pypi.tuna.tsinghua.edu.cn/simple`

### 安装步骤

1. **安装 Docling**：

```bash
pip install docling
```

2. **复制技能文件**到 Claude Code 技能目录：

```bash
# Linux / macOS
cp SKILL.md ~/.claude/skills/docling/SKILL.md

# Windows (PowerShell)
Copy-Item SKILL.md $env:USERPROFILE\.claude\skills\docling\SKILL.md
```

3. **重启 Claude Code**（或开启新会话），技能自动加载。

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

```bash
# 转换整个目录
docling ./documents/ --to md --output ./converted/

# 从 URL 转换
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
| `docling: command not found` | 确认 Python Scripts 目录在 PATH 中，或使用 `python -m docling` |
| HuggingFace symlink 警告（Windows） | 仅影响显示。设置 `HF_HUB_DISABLE_SYMLINKS_WARNING=1` 抑制 |
| 转换速度慢 | 首次运行需下载 ~550MB 模型。缓存后矢量 PDF 秒级完成 |
| OCR 效果差 | 尝试 `--force-ocr` 或 `--ocr-engine tesseract` |
| 大文件内存不足 | 分批处理，或使用 `--no-tables` 减少内存占用 |

### 许可证

MIT License。详见 [LICENSE](LICENSE)。

### 致谢

- [Docling](https://github.com/docling-project/docling) — IBM Research
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — Anthropic
