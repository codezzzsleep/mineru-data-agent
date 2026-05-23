from __future__ import annotations


def infer_profile(task: str, filename: str) -> str:
    text = f"{task} {filename}".lower()
    if any(word in text for word in ["财报", "报表", "资产", "负债", "利润", "cash", "finance", "table"]):
        return "financial_report"
    if any(word in text for word in ["规范", "标准", "条款", "合同", "standard", "clause"]):
        return "standard_or_contract"
    if any(word in text for word in ["流程", "工艺", "工程图", "图纸", "flow", "diagram"]):
        return "workflow_or_diagram"
    if any(word in text for word in ["扫描", "拍照", "模糊", "低质量", "ocr", "scan"]):
        return "low_quality_ocr"
    return "general_document"


def build_plan(task: str, profile: str) -> list[str]:
    common = [
        "Inspect input type and task objective",
        "Parse document with MinerU or native HTML extractor",
        "Normalize content blocks with page-level or document-level provenance",
        "Build markdown, section, key-value, table, and numeric views",
        "Run quality checks and produce traceable logs",
    ]
    profile_steps = {
        "financial_report": [
            "Prioritize dense table extraction and numeric consistency checks",
            "Flag subtotal/total rows and suspicious numeric cells",
        ],
        "standard_or_contract": [
            "Prioritize section hierarchy and clause-like paragraph extraction",
            "Preserve source page or document heading evidence for each clause",
        ],
        "workflow_or_diagram": [
            "Prioritize figure/image references and ordered procedural statements",
            "Flag pages that need visual model follow-up",
        ],
        "low_quality_ocr": [
            "Prioritize OCR confidence proxies and mojibake/noise checks",
            "Flag pages with sparse extracted text for manual or VLM fallback",
        ],
    }
    return common + profile_steps.get(profile, [])
