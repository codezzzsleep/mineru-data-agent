# MinerU Data Agent Run 31921e2b4f8f

- Task: 分析低质量 OCR 文本，抽取日期、异常温度、编码噪声和处理建议。
- Profile: low_quality_ocr
- Input: `<PROJECT_ROOT>\examples\cases\case_2_low_quality_ocr.html`
- Quality: pass (100/100)
- Content blocks: 10
- Pages with provenance: 0
- Provenance level: document
- Sections: 2
- Tables: 0
- Key-values: 5
- Numeric facts: 2
- Dates detected: 1
- Recommendation signals: 2
- Anomaly signals: 5
- Retrieval chunks: 2
- Recovery decision: recovered_accept
- Recovery selected attempt: text_cleanup
- Recovery attempts: 2
- LLM analysis: disabled

## Plan
1. Inspect input type and task objective
2. Parse document with MinerU or native HTML extractor
3. Normalize content blocks with page-level or document-level provenance
4. Build markdown, section, key-value, table, and numeric views
5. Run quality checks and produce traceable logs
6. Prioritize OCR confidence proxies and mojibake/noise checks
7. Flag pages with sparse extracted text for manual or VLM fallback

## Extracted Fields
- 报告日期: 2026-05-18
- 文档来源: 车间安全巡检拍照件，存在轻微倾斜、局部反光、签章覆盖和手写批注。
- OCR 摘要: 第 2 页温度记录可读，第 3 页签章区域存在样编码噪声，第 4 页边缘文字残缺。
- 异常提示: 设备 B-17 的温度记录出现 86.5 摄氏度，超过阈值 80 摄氏度，需要人工复核原图。
- 处理建议: 对低清晰度区域启用更高分辨率重扫或 VLM 复核，并把噪声行写入质量报告。

## Recommendation Evidence
- 处理建议: 对低清晰度区域启用更高分辨率重扫或 VLM 复核，并把噪声行写入质量报告。
- 处理建议：对低清晰度区域启用更高分辨率重扫或 VLM 复核，并把噪声行写入质量报告。

## Recovery Decision
- Decision: recovered_accept
- Executed 1 automatic recovery attempt(s); selected `text_cleanup`.
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.
- Initial quality issues were preserved for audit: possible_mojibake, document_level_provenance.

Attempts:
- initial: pass_with_warnings (92/100), not selected
- text_cleanup: pass (100/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.

## Markdown Preview

# 低质量扫描件 OCR 复核记录

报告日期：2026-05-18

文档来源：车间安全巡检拍照件，存在轻微倾斜、局部反光、签章覆盖和手写批注。

OCR 摘要：第 2 页温度记录可读，第 3 页签章区域存在样编码噪声，第 4 页边缘文字残缺。

异常提示：设备 B-17 的温度记录出现 86.5 摄氏度，超过阈值 80 摄氏度，需要人工复核原图。

处理建议：对低清晰度区域启用更高分辨率重扫或 VLM 复核，并把噪声行写入质量报告。

## 复核清单

- 检查页边裁切是否导致表格列名丢失。

- 检查手写签章是否覆盖设备编号。

- 检查异常温度数值是否来自同一行。
