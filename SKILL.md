---
name: docling
description: 使用 Docling 将单个本地 PDF 转为 Markdown、结构化 JSON、HTML、文本或检索分块。用户要求 Docling PDF 转换、扫描 PDF 的 OCR 或 PDF 表格与公式提取时使用。仅处理一个 PDF，不处理目录、批量文件、音视频或其他输入格式。
---

# Docling：Claude Code 与 Codex 单 PDF 转换

## 调用与范围

Claude Code 使用 `/docling`，Codex 使用 `$docling`；两者也可根据用户明确的 PDF 转换请求选择本技能。根据当前平台提供的技能绝对路径定位脚本，流程只依赖本地 Python，不依赖某个平台专有工具。使用本技能目录下的 `scripts/convert_single.py`，调用时使用脚本的绝对路径。只接收一个本地 `.pdf` 文件；URL 先下载后传本地路径。从当前消息和附件上下文取得文件路径；用户已给出路径和格式时直接执行，缺少输入路径才询问。输出默认 Markdown。

已验证环境：Python 3.12、Docling 2.115.0、pypdf 6.13.0。依赖列在 `requirements.txt`；其他版本需留意转换报告的版本警告。使用调用脚本的同一 Python 环境运行 Docling，避免 PATH 指向另一环境。

## 工作流程

1. 验证 PDF 路径与文件头。目录、多个文件和非 PDF 输入直接拒绝。
2. 由入口自动运行 PDF 分析，无需额外重复检测。默认均匀采样最多 7 页，覆盖首尾与中间页面。解析错误直接报告，不当成加密。
3. 加密且无法打开时索取密码，然后通过 `DOCLING_PDF_PASSWORD` 环境变量传入，重新执行。不会自动安装依赖或改名源文件。
4. 合并检测建议与用户参数。用户显式指定的 OCR、表格选项优先；冲突参数直接拒绝。未检查全部页面时保持 OCR 开启。
5. 执行标准 PDF 管线。每次在输出父目录下创建唯一的 `<原名>_docling_<后缀>` 子目录，避免覆盖旧结果。显式传入 `--output`：用户指定目录优先，否则使用当前任务约定的交付目录；未约定时使用 PDF 所在目录。若用户要求原目录同名文件，验证后将所需产物复制为原目录中的同名文件，日志与结构副本留在转换子目录。
6. 验证实际产物存在、非空，结构副本符合 DoclingDocument 模式且页数与输入一致。保存日志和 JSON 报告；只有验证通过才返回退出码 0。
7. 向用户报告实际文件路径、大小、耗时、检测与使用参数，以及需要检查的内容。结构验证不能证明文字、公式、表格识别准确，出现空正文或警告时需抽查对应页面。

## 调用示例

以下脚本路径需替换为本技能中脚本的绝对路径：

```powershell
python "<技能绝对路径>\scripts\convert_single.py" "C:\papers\paper.pdf" --output "<任务交付目录>" --json
python "<技能绝对路径>\scripts\convert_single.py" "C:\papers\paper.pdf" --to json --output "C:\papers\converted" --json
python "<技能绝对路径>\scripts\convert_single.py" "C:\papers\scan.pdf" --force-ocr --ocr-engine easyocr --ocr-lang ch_sim,en --json
python "<技能绝对路径>\scripts\convert_single.py" "C:\papers\paper.pdf" --enrich-formula --table-mode accurate --timeout 1200 --json
```

其他参数用 `--help` 查看。支持 `md/json/yaml/html/html_split_page/text/doctags/doclang/chunks`。`doclang` 实际生成 `.dclg.xml`。`chunks` 实际生成 `.chunks.jsonl`，`html_split_page` 生成带分页视图的单个 `.html`。转换同时保留 `.json` 结构副本、`conversion.log` 和 `conversion-report.json`。

## 检测与参数边界

- 类型包含 `vector_text/scanned/mixed/form/encrypted/unknown`。表单、扫描和公式线索是独立特征，表单类型不意味着可以禁用 OCR。
- 只有全部页面均已检查、每页有文本且无图片、检测无异常时，才自动建议 `--no-ocr`；采样扫描页且无文本时建议 `--force-ocr`。
- 无文本时语言返回 `unknown`，不猜英文。语言由可提取文本判断，不证明扫描图片的语言。
- 公式为启发式线索，不自动启动额外模型；用户需要时使用 `--enrich-formula`。图表参数为 `--enrich-chart-extraction`。
- OCR 默认引擎为 `auto`。指定 `--ocr-lang` 时必须同时指定引擎；EasyOCR 使用 `ch_sim,en`，Tesseract 使用 `chi_sim,eng`。不要把 `zh,en` 作为所有引擎的通用参数。
- 首次运行可能下载所需模型；不同 OCR、公式增强和分块选项的模型与空间开销不同，不承诺固定下载量或固定耗时。

## 故障处理与验证

转换失败时先读取报告的 `error` 和日志，不把任何失败都归因于缺少 Docling。当前 Python 环境缺依赖时说明原因，用户同意安装后运行 `python -m pip install -r "<技能绝对路径>\requirements.txt"`。

密码缺失或错误：取得正确密码后重试。文件损坏：请求有效 PDF。超时：检查日志与页数，必要时增加 `--timeout`。缺失、空白、页数不匹配的产物：保留失败目录，修正具体原因后重试。Windows 中文路径报错时先定位日志；需要兼容副本时复制源 PDF 到临时路径，不重命名源文件。

单独诊断可使用 `scripts/detect_pdf_type.py input.pdf --json`。回归测试命令：

```powershell
python -m unittest discover -s "<技能绝对路径>\tests" -v
```
