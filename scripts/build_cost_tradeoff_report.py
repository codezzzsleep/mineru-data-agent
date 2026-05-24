"""Build a cost + speed + quality tradeoff table from scenario assumptions.

Default price inputs are illustrative May 2026 assumptions captured for reviewer
sensitivity analysis. They are not contractual pricing claims and should be
replaced with current provider quotes before production cost planning.

Also records an ablation attempt: same fixture -> rule-based vs LLM-enabled,
comparing saved-label checks, token usage, wall time, and evidence completeness.
"""

from __future__ import annotations

import json
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mineru_data_agent.agent import MinerUDataAgent
from mineru_data_agent.agent_live import run_live_agent

OUT_DIR = ROOT / "submission_artifacts" / "cost_model"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Illustrative May 2026 scenario inputs.
GPU_CNY_PER_HOUR = 8.00
MINERU_API_CNY_PER_PAGE = 0.15
LLM_INPUT_CNY_PER_1M = 1.00
LLM_OUTPUT_CNY_PER_1M = 2.00
ASSUMED_PAGES_PER_PDF = 10
ASSUMED_INPUT_TOKENS_PER_DOC = 1500
ASSUMED_OUTPUT_TOKENS_PER_DOC = 800

ABLATION_CASE = ROOT / "examples" / "cases" / "case_1_financial_report.html"
ABLATION_OUT = ROOT / "runs" / "ablation"


def run_rule_based(case: Path, task: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    agent = MinerUDataAgent()
    result = agent.run(
        input_file=case,
        output_root=ABLATION_OUT,
        task=task,
        profile="auto",
    )
    elapsed = time.perf_counter() - t0
    return {
        "mode": "rule_based",
        "elapsed_seconds": round(elapsed, 2),
        "quality_score": result.quality.get("score"),
        "quality_status": result.quality.get("status"),
        "issue_count": result.quality.get("issue_count", 0),
        "extracted_sections": len(result.extracted.get("sections", [])),
        "extracted_tables": len(result.extracted.get("tables", [])),
        "has_llm_analysis": bool(result.llm_analysis.get("enabled")),
    }


def run_llm_enabled(case: Path, task: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    trace = run_live_agent(
        input_file=case,
        output_root=ABLATION_OUT / "llm",
        task=task,
        provider="modelscope",
        model="Qwen/Qwen3-235B-A22B-Instruct-2507",
        max_turns=12,
    )
    elapsed = time.perf_counter() - t0
    return {
        "mode": "llm_driven",
        "elapsed_seconds": round(elapsed, 2),
        "agent_status": trace.status,
        "turns": len(trace.turns),
        "tokens_prompt": trace.prompt_tokens,
        "tokens_completion": trace.completion_tokens,
        "tokens_total": trace.total_tokens,
        "llm_cost_estimate_cny": round(
            (trace.prompt_tokens / 1_000_000) * LLM_INPUT_CNY_PER_1M
            + (trace.completion_tokens / 1_000_000) * LLM_OUTPUT_CNY_PER_1M,
            4,
        ),
        "has_final_answer": bool(trace.final_answer),
        "evidence_count": len(trace.final_evidence),
    }


def build_tradeoff_table() -> list[dict[str, Any]]:
    return [
        {
            "path": "Native HTML/Office (rule-based, CPU)",
            "quality_label_check": "saved-label pass on covered fixtures",
            "cost_per_100_docs_cny": 0.00,
            "time_per_100_docs_minutes": "< 1",
            "page_provenance": "document-level",
            "recovery": "encoding noise / OCR retry (rule-triggered)",
            "best_for": "HTML pages, DOCX, PPTX — any input already in text form",
        },
        {
            "path": "MinerU Agent API (online, CPU)",
            "quality_label_check": "same parser quality as CLI but no page-level provenance",
            "cost_per_100_docs_cny": round(100 * ASSUMED_PAGES_PER_PDF * MINERU_API_CNY_PER_PAGE, 0),
            "time_per_100_docs_minutes": "5–15",
            "page_provenance": "no (API returns inline markdown without page break markers)",
            "recovery": "CLI fallback if page provenance required",
            "best_for": "Quick PDF parsing in CPU-only env, content extraction without audit needs",
        },
        {
            "path": "MinerU CLI (local, GPU)",
            "quality_label_check": "saved-label pass on covered CLI fixtures, with page provenance",
            "cost_per_100_docs_cny": round(100 * ASSUMED_PAGES_PER_PDF * (GPU_CNY_PER_HOUR / 3600 * 5), 0),
            "time_per_100_docs_minutes": "8–20 (5s per page @ 10pp doc)",
            "page_provenance": "full (page-level markers, middle/model artifacts)",
            "recovery": "OCR retry for low-quality pages",
            "best_for": "PDF audits, research requiring layout/model artifacts, large OCR batches",
        },
        {
            "path": "MinerU CLI (沐曦 competition GPU, free)",
            "quality_label_check": "same as CLI above",
            "cost_per_100_docs_cny": 0.00,
            "time_per_100_docs_minutes": "8–20",
            "page_provenance": "full",
            "recovery": "same as CLI above",
            "best_for": "Competition submission — use 沐曦 resource for all PDF-heavy cases at zero cost",
        },
        {
            "path": "LLM-enabled (DeepSeek V4-Flash)",
            "quality_label_check": "LLM-assisted review path; quality must be judged from saved answer-quality fields, not assumed from token use",
            "cost_per_100_docs_cny": round(
                100
                * (
                    ASSUMED_INPUT_TOKENS_PER_DOC * LLM_INPUT_CNY_PER_1M / 1_000_000
                    + ASSUMED_OUTPUT_TOKENS_PER_DOC * LLM_OUTPUT_CNY_PER_1M / 1_000_000
                ),
                2,
            ),
            "time_per_100_docs_minutes": "10–30 (LLM adds 15–30s per doc)",
            "page_provenance": "depends on underlying parser",
            "recovery": "LLM-driven: reads validator codes, decides clean_text or reparse, replans",
            "best_for": "Complex tasks: semantic extraction, compliance judgment, multi-doc cross-ref, custom schema",
        },
        {
            "path": "LLM-enabled (Qwen3 via ModelScope free)",
            "quality_label_check": "same LLM-assisted path; quota and answer quality vary by run",
            "cost_per_100_docs_cny": 0.00,
            "time_per_100_docs_minutes": "10–30",
            "page_provenance": "depends on underlying parser",
            "recovery": "same LLM-driven as above",
            "best_for": "Zero-cost LLM augmentation for competition; limited by daily quota",
        },
    ]


def run_ablation() -> dict[str, Any]:
    task = "识别 2026Q1 营业收入和利润总额，验证合计行是否一致"
    results = {}

    print("Ablation: rule-based...")
    results["rule_based"] = run_rule_based(ABLATION_CASE, task)

    print("Ablation: LLM-driven (skip if quota exhausted)...")
    try:
        results["llm_driven"] = run_llm_enabled(ABLATION_CASE, task)
    except Exception as exc:
        results["llm_driven"] = {"error": str(exc)}
        print(f"  skipped: {exc}")

    return results


def live_evidence_available() -> bool:
    report_path = ROOT / "submission_artifacts" / "agent_live_cases" / "agent_live_report.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    cases = report.get("cases", []) if isinstance(report.get("cases"), list) else []
    return any(isinstance(case, dict) and case.get("live_evidence") for case in cases)


def main() -> int:
    tradeoff = build_tradeoff_table()

    print("Running ablation experiment...")
    ablation = run_ablation()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pricing_assumptions": {
            "gpu_cny_per_hour": GPU_CNY_PER_HOUR,
            "mineru_api_cny_per_page": MINERU_API_CNY_PER_PAGE,
            "llm_input_cny_per_1m_tokens": LLM_INPUT_CNY_PER_1M,
            "llm_output_cny_per_1m_tokens": LLM_OUTPUT_CNY_PER_1M,
            "assumed_pages_per_pdf": ASSUMED_PAGES_PER_PDF,
            "notes": "Illustrative May 2026 scenario inputs for sensitivity analysis; replace with current provider quotes before production cost planning. ModelScope free-tier and competition GPU assumptions are quota/resource dependent.",
        },
        "tradeoff_table": tradeoff,
        "ablation": ablation,
        "live_evidence_available": live_evidence_available(),
    }

    (OUT_DIR / "cost_model.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "cost_model.md").write_text(
        _render(report), encoding="utf-8"
    )

    print(f"\nReport written to {OUT_DIR}")
    return 0


def _render(report: dict) -> str:
    t = report["tradeoff_table"]
    p = report["pricing_assumptions"]
    ab = report["ablation"]

    lines = [
        "# Cost / Speed / Quality Tradeoff",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Scenario Price Inputs (Illustrative May 2026)",
        "",
        f"- GPU scenario input: ¥{p['gpu_cny_per_hour']:.2f}/hour",
        f"- MinerU Agent API scenario input: ¥{p['mineru_api_cny_per_page']:.2f}/page",
        f"- DeepSeek V4-Flash scenario input: ¥{p['llm_input_cny_per_1m_tokens']:.2f}/1M input, ¥{p['llm_output_cny_per_1m_tokens']:.2f}/1M output tokens",
        f"- Assumed PDF size: {p['assumed_pages_per_pdf']} pages",
        f"- ModelScope Qwen3-235B scenario input: ¥0 for quota-limited/free-tier runs",
        f"- MinerU沐曦 GPU scenario input: ¥0 for allocated competition resources",
        f"- Boundary: {p['notes']}",
        "",
        "## Tradeoff Matrix",
        "",
        "| Path | Quality evidence | Illustrative ¥ per 100 docs | Time per 100 docs | Page provenance | Recovery |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for row in t:
        lines.append(
            f"| {row['path']} | {row['quality_label_check']} | "
            f"{row['cost_per_100_docs_cny']} | {row['time_per_100_docs_minutes']} | "
            f"{row['page_provenance']} | {row['recovery']} |"
        )

    lines.extend([
        "",
        "## Ablation Attempt: Rule-based vs LLM-driven (same fixture)",
        "",
    ])
    for mode, data in ab.items():
        lines.append(f"### {mode}")
        for k, v in data.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    lines.extend([
        "## Decision Tree",
        "",
        "- **Input is HTML/DOCX/PPTX** → rule-based agent (free, fast)",
        "- **PDF, need page provenance** → local MinerU CLI (GPU or 沐曦)",
        "- **PDF, CPU-only, no audit** → MinerU Agent API (cost depends on current provider/page pricing)",
        "- **Complex task** (semantic judgment, schema generation, compliance) → LLM-assisted agent with answer-quality review",
        "  - **Quota-limited low-cost trial** → Qwen3 via ModelScope when free-tier quota is available",
        "  - **Production** → price from current provider quote and observed token usage, not this illustrative table alone",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
