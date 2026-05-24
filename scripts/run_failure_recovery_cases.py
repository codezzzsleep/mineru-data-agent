from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from mineru_data_agent.agent import MinerUDataAgent
from mineru_data_agent.mineru_client import MinerUParseError
from mineru_data_agent.models import ParseArtifacts, ToolCall


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = PROJECT_ROOT / "runs" / "failure_recovery_cases"
DEST_ROOT = PROJECT_ROOT / "submission_artifacts" / "failure_recovery_cases"


CASES = [
    {
        "id": "text_cleanup_mojibake",
        "kind": "native_html",
        "task": "清理 OCR 噪声合同并保留质量问题。",
        "profile": "low_quality_ocr",
        "expected_decision": "recovered_with_review_notes",
        "expected_selected_attempt": "text_cleanup",
        "boundary": "native HTML controlled fixture; validates text cleanup recovery path",
    },
    {
        "id": "ocr_retry_success_controlled",
        "kind": "ocr_retry_success",
        "task": "解析稀疏 PDF；初始文本过短时切到 OCR。",
        "profile": "general_document",
        "expected_decision": "recovered_accept",
        "expected_selected_attempt": "ocr_retry",
        "boundary": "controlled fake MinerU runner; validates retry selection logic, not live OCR quality",
    },
    {
        "id": "ocr_retry_failure_controlled",
        "kind": "ocr_retry_failure",
        "task": "解析稀疏 PDF；记录 OCR 重试失败后的保底结果。",
        "profile": "general_document",
        "expected_decision": "retry_or_manual_review",
        "expected_selected_attempt": "initial",
        "boundary": "controlled fake MinerU runner; validates failed-attempt audit trail",
    },
    {
        "id": "strict_provenance_failure_controlled",
        "kind": "strict_provenance_failure",
        "task": "解析 PDF，并要求字段能追溯到页级来源。",
        "profile": "standard_or_contract",
        "expected_decision": "strict_page_provenance_failed",
        "expected_selected_attempt": "initial",
        "boundary": "controlled fake online-API runner; validates strict provenance gate without claiming live API behavior",
    },
    {
        "id": "numeric_total_mismatch_html",
        "kind": "numeric_total_mismatch",
        "task": "检查财报表格总计是否一致，并标记人工复核项。",
        "profile": "financial_report",
        "expected_decision": "manual_numeric_review",
        "expected_selected_attempt": "initial",
        "boundary": "native HTML controlled fixture; validates numeric mismatch detection",
    },
]


def main() -> None:
    if DEST_ROOT.exists():
        shutil.rmtree(DEST_ROOT)
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    input_root = RUN_ROOT / "_inputs"
    input_root.mkdir(parents=True, exist_ok=True)

    rows = [
        "# Failure And Recovery Cases",
        "",
        "These are controlled fault-injection cases. They check failure detection, retry decisions, and audit fields. They are not public-network, GPU, or live OCR benchmarks.",
        "",
        "| Case | Trigger | Decision | Selected Attempt | Final Quality | Boundary |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    index = []
    for case in CASES:
        result = run_case(case, input_root)
        validate_expected_case_result(case, result)
        case_dir = DEST_ROOT / case["id"]
        shutil.copytree(Path(result.output_dir), case_dir)
        input_path = Path(result.input_file)
        if input_path.exists():
            shutil.copy2(input_path, case_dir / f"input{input_path.suffix.lower()}")
        mark_boundary(case_dir, case)
        sanitize_tree(case_dir)

        issue_codes = [
            str(item)
            for item in (
                result.recovery_decision.get("initial_issue_codes")
                or [issue.get("code") for issue in result.quality.get("issues", []) if isinstance(issue, dict)]
            )
            if item
        ]
        rows.append(
            "| {case_id} | {issues} | {decision} | {selected} | {quality} ({score}) | {boundary} |".format(
                case_id=case["id"],
                issues=", ".join(issue_codes) or "-",
                decision=result.recovery_decision.get("decision"),
                selected=result.recovery_decision.get("selected_attempt"),
                quality=result.quality.get("status"),
                score=result.quality.get("score"),
                boundary=case["boundary"],
            )
        )
        index.append(
            {
                "id": case["id"],
                "trigger_issue_codes": issue_codes,
                "decision": result.recovery_decision.get("decision"),
                "selected_attempt": result.recovery_decision.get("selected_attempt"),
                "attempts": result.recovery_decision.get("attempts", []),
                "quality_status": result.quality.get("status"),
                "quality_score": result.quality.get("score"),
                "result_path": display_path(case_dir / "result.json"),
                "trace_path": display_path(case_dir / "trace.json"),
                "boundary": case["boundary"],
            }
        )

    (DEST_ROOT / "README.md").write_text("\n".join(rows).strip() + "\n", encoding="utf-8")
    index_payload = {
        "boundary": "controlled fault injection; not a live OCR/network/GPU benchmark",
        "cases": index,
    }
    (DEST_ROOT / "artifact_index.json").write_text(_scrub_paths(json.dumps(index_payload, ensure_ascii=False, indent=2)), encoding="utf-8")
    print(json.dumps({"dest": display_path(DEST_ROOT), "cases": [case["id"] for case in CASES]}, ensure_ascii=False))


def run_case(case: dict[str, Any], input_root: Path) -> Any:
    kind = case["kind"]
    input_path = input_root / f"{case['id']}.{'html' if kind in {'native_html', 'numeric_total_mismatch'} else 'pdf'}"
    if kind == "native_html":
        input_path.write_text(_mojibake_html(), encoding="utf-8")
        agent = MinerUDataAgent()
        return agent.run(input_path, RUN_ROOT, task=case["task"], profile=case["profile"])
    if kind == "numeric_total_mismatch":
        input_path.write_text(_numeric_mismatch_html(), encoding="utf-8")
        agent = MinerUDataAgent()
        return agent.run(input_path, RUN_ROOT, task=case["task"], profile=case["profile"])
    input_path.write_bytes(b"%PDF-1.4\n% controlled fault injection")
    if kind == "ocr_retry_success":
        agent = MinerUDataAgent(mineru_runner=_SparseThenOcrRunner())
        return agent.run(input_path, RUN_ROOT, task=case["task"], profile=case["profile"], method="auto")
    if kind == "ocr_retry_failure":
        agent = MinerUDataAgent(mineru_runner=_SparseThenOcrFailingRunner())
        return agent.run(input_path, RUN_ROOT, task=case["task"], profile=case["profile"], method="auto")
    if kind == "strict_provenance_failure":
        agent = MinerUDataAgent(mineru_runner=_NoProvenanceRunner())
        return agent.run(
            input_path,
            RUN_ROOT,
            task=case["task"],
            profile=case["profile"],
            strict_page_provenance=True,
        )
    raise ValueError(f"Unknown case kind: {kind}")


def validate_expected_case_result(case: dict[str, Any], result: Any) -> None:
    decision = result.recovery_decision.get("decision")
    selected = result.recovery_decision.get("selected_attempt")
    if decision != case["expected_decision"]:
        raise AssertionError(f"{case['id']} expected decision {case['expected_decision']!r}, got {decision!r}")
    if selected != case["expected_selected_attempt"]:
        raise AssertionError(
            f"{case['id']} expected selected attempt {case['expected_selected_attempt']!r}, got {selected!r}"
        )


class _SparseThenOcrRunner:
    def parse(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
    ) -> tuple[ParseArtifacts, ToolCall]:
        base = output_dir / input_path.stem / method
        base.mkdir(parents=True, exist_ok=True)
        markdown_path = base / f"{input_path.stem}.md"
        content_path = base / f"{input_path.stem}_content_list.json"
        if method == "ocr":
            markdown = "# OCR Recovery\n\n报告日期：2026-05-24\n\n" + ("OCR recovery produced page-level text. " * 24)
            content = [{"type": "text", "text": markdown, "page_idx": 0, "source": "controlled-ocr"}]
        else:
            markdown = "too short"
            content = [{"type": "text", "text": markdown, "page_idx": 0, "source": "controlled-initial"}]
        markdown_path.write_text(markdown, encoding="utf-8")
        content_path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        return (
            ParseArtifacts(markdown_path=markdown_path, content_list_path=content_path),
            ToolCall("controlled-mineru", ["controlled-mineru", method], "completed", 0.01),
        )


class _SparseThenOcrFailingRunner(_SparseThenOcrRunner):
    def parse(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
    ) -> tuple[ParseArtifacts, ToolCall]:
        if method == "ocr":
            call = ToolCall("controlled-mineru", ["controlled-mineru", method], "failed", 0.01, stderr_tail="controlled OCR failure")
            raise MinerUParseError("controlled OCR failure", call)
        return super().parse(input_path, output_dir, backend=backend, method=method, lang=lang)


class _NoProvenanceRunner:
    def parse(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
    ) -> tuple[ParseArtifacts, ToolCall]:
        base = output_dir / input_path.stem / "agent_api"
        base.mkdir(parents=True, exist_ok=True)
        markdown_path = base / f"{input_path.stem}.md"
        content_path = base / f"{input_path.stem}_content_list.json"
        markdown = "# Contract\n\nContract No: STRICT-001\n\n" + ("Document-level text without page evidence. " * 18)
        content = [
            {"type": "heading", "text": "# Contract", "source": "controlled-agent-api"},
            {"type": "text", "text": "Contract No: STRICT-001", "source": "controlled-agent-api"},
            {"type": "text", "text": "Document-level text without page evidence. " * 18, "source": "controlled-agent-api"},
        ]
        markdown_path.write_text(markdown, encoding="utf-8")
        content_path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        return (
            ParseArtifacts(markdown_path=markdown_path, content_list_path=content_path),
            ToolCall("controlled-agent-api", ["controlled-agent-api", method], "completed", 0.01),
        )


def _mojibake_html() -> str:
    return """
<html><body>
<h1>OCR 噪声合同</h1>
<p>合同编号：NOISE-001</p>
<p>签署日期：2026-05-24</p>
<p>锟斤拷锟斤拷锟斤拷""" + ("需要清理的合同正文。 " * 36) + """</p>
</body></html>
"""


def _numeric_mismatch_html() -> str:
    return """
<html><body>
<h1>财报总计校验负样本</h1>
<table>
<tr><th>项目</th><th>金额</th></tr>
<tr><td>硬件收入</td><td>100</td></tr>
<tr><td>软件收入</td><td>200</td></tr>
<tr><td>合计</td><td>400</td></tr>
</table>
<p>本样本故意让合计行不等于明细行之和，用于验证 numeric_total_mismatch。</p>
</body></html>
"""


def mark_boundary(case_dir: Path, case: dict[str, Any]) -> None:
    boundary = {
        "controlled_fault_injection": True,
        "not_live_benchmark": True,
        "boundary": case["boundary"],
    }
    for filename in ("result.json", "trace.json"):
        path = case_dir / filename
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["fault_injection_boundary"] = boundary
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path = case_dir / "summary.md"
    if summary_path.exists():
        text = summary_path.read_text(encoding="utf-8")
        summary_path.write_text(f"> Boundary: {case['boundary']}.\n\n{text}", encoding="utf-8")


def sanitize_tree(path: Path) -> None:
    for item in path.rglob("*"):
        if not item.is_file() or item.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".html"}:
            continue
        text = item.read_text(encoding="utf-8", errors="replace")
        item.write_text(_scrub_paths(text), encoding="utf-8")


def _scrub_paths(text: str) -> str:
    clean = text.replace(str(PROJECT_ROOT), "<PROJECT_ROOT>")
    clean = clean.replace(str(PROJECT_ROOT).replace("\\", "\\\\"), "<PROJECT_ROOT>")
    return clean


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
