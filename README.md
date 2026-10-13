# Docling Skill

面向 **Claude Code 与 Codex** 的单 PDF 转换技能。一个 `SKILL.md`、同一组 Python 脚本，在两种智能体中使用相同的分析、转换与验证流程。

只处理一个本地 PDF，默认输出 Markdown。支持文本 PDF、扫描 PDF、混合页面和表单；不提供批量或多智能体并行处理。

## 安装

获取仓库：

```bash
git clone https://github.com/Issac-qjxz/docling-skill.git
cd docling-skill
python -m pip install -r requirements.txt
```

将以下文件复制到对应平台的个人技能目录，并保留目录结构：

```text
SKILL.md
requirements.txt
scripts/
agents/
tests/
```

| 平台 | 个人安装目录 | 显式调用 |
|---|---|---|
| Claude Code | `~/.claude/skills/docling/` | `/docling` |
| Codex | `~/.agents/skills/docling/` | `$docling` |

Windows 的 `~` 对应用户目录，例如 `C:\Users\你的用户名`。复制时排除 `.git`、`.bak` 和 `__pycache__`。在新一轮对话中使用；若技能未出现，重启对应应用。

Windows PowerShell 安装示例，在仓库根目录运行：

```powershell
# Claude Code
$skillDir = Join-Path $env:USERPROFILE '.claude\skills\docling'
New-Item -ItemType Directory -Force -Path $skillDir | Out-Null
Copy-Item -Path SKILL.md,requirements.txt -Destination $skillDir
Copy-Item -Recurse -Path scripts,agents,tests -Destination $skillDir

# Codex
$skillDir = Join-Path $env:USERPROFILE '.agents\skills\docling'
New-Item -ItemType Directory -Force -Path $skillDir | Out-Null
Copy-Item -Path SKILL.md,requirements.txt -Destination $skillDir
Copy-Item -Recurse -Path scripts,agents,tests -Destination $skillDir
```

以上命令适用于新安装；已有同名技能时先备份，再替换对应文件。

## 使用

Claude Code：

```text
/docling 将 "C:\papers\paper.pdf" 转为 Markdown，放在原目录，保留原名。
```

Codex：

```text
$docling 将 "C:\papers\paper.pdf" 转为 Markdown，放在原目录，保留原名。
```

也可以直接运行脚本，无需使用智能体：

```bash
python scripts/convert_single.py input.pdf --to md --output ./converted --json
python scripts/convert_single.py scan.pdf --force-ocr --ocr-engine easyocr --ocr-lang ch_sim,en --json
python scripts/convert_single.py paper.pdf --enrich-formula --timeout 1200 --json
```

参数详情见 `python scripts/convert_single.py --help`。入口自动完成 PDF 检测，不需要先单独运行检测脚本。

## 输出与验证

每次创建独立的 `<原名>_docling_<后缀>` 结果目录，避免旧文件影响成功判定。结果包含所选格式、JSON 结构副本、`conversion.log` 和 `conversion-report.json`。

只有命令成功、产物存在且非空、结构副本通过 DoclingDocument 验证、页数与输入一致时，才返回退出码 0。文字、表格和公式识别准确率仍需结合原页面抽查。

| 输出参数 | 文件后缀 |
|---|---|
| `md` | `.md` |
| `json` / `yaml` | `.json` / `.yaml` |
| `html` / `html_split_page` | `.html`，后者为同一文件中的分页视图 |
| `text` / `doctags` / `doclang` | `.txt` / `.doctags` / `.dclg.xml` |
| `chunks` | `.chunks.jsonl` |

## 环境与边界

- Python 最低版本 3.10；已验证 Python 3.12、Docling 2.115.0、pypdf 6.13.0。依赖版本固定在 `requirements.txt`。
- 默认分散采样最多 7 页。未检查全部页面时保留 OCR；语言未知时明确返回 `unknown`。
- 用户显式指定的 OCR 和表格参数优先。互相冲突的参数会被拒绝。
- OCR 语言代码取决于引擎：EasyOCR 使用 `ch_sim,en`，Tesseract 使用 `chi_sim,eng`。`auto` 引擎不接受语言覆盖。
- 加密 PDF 可通过 `DOCLING_PDF_PASSWORD` 环境变量传入密码；报告和日志会隐藏密码。
- Windows 中文文件名遇到 Docling 临时文件错误时，使用英文名临时副本转换，然后恢复产物名称；保留源 PDF。曾在 118 页中文 PDF 上验证此流程。
- 首次使用部分功能可能下载模型；下载量和耗时取决于所选功能及本机缓存。

## 测试

```bash
python -X utf8 -m unittest discover -s tests -v
```

23 个回归测试覆盖 PDF 检测、参数冲突、旧产物干扰、缺失产物、密码解密、超时、页数一致性和 UTF-8 输出。测试随机种子固定为 0，不下载转换模型。

## License

[MIT](LICENSE)。文档解析能力来自 [Docling](https://github.com/docling-project/docling)。
