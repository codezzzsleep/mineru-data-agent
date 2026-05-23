from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from mineru_data_agent.agent import MinerUDataAgent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "examples" / "challenge_manifest.json"
RUN_ROOT = PROJECT_ROOT / "runs" / "challenge_cases"
DEST_ROOT = PROJECT_ROOT / "submission_artifacts" / "challenge_cases"


ANNOTATIONS = {
    "case_6_cross_page_financial_table": {
        "Document ID": "FIN-CROSS-2026-06",
        "Reporting Period": "2026-01-01 to 2026-03-31",
        "Owner": "Finance Shared Service Center",
        "Expected risk": "subtotal and total rows are separated by a page break",
    },
    "case_7_noisy_contract_scan": {
        "Contract No": "OCR-NOISE-2026-17",
        "Effective Date": "2026-05-21",
        "Expected recovery": "text cleanup recovery",
        "Expected issue": "possible_mojibake",
    },
    "case_8_industry_standard_matrix": {
        "Standard ID": "STD-MATRIX-2026-09",
        "Review Date": "2026-05-22",
        "Owner": "Quality Engineering Office",
        "Critical requirement": "secret scan excludes API keys",
        "Recovery linkage": "PDF recovery evidence records executed=true",
    },
    "case_9_incident_workflow_report": {
        "Incident ID": "OPS-INC-2026-0519",
        "Report Date": "2026-05-23",
        "Referenced selected attempt": "cli_fallback in the separate PDF recovery case",
        "Referenced action": "route no_page_provenance to CLI fallback when a CLI environment is available",
    },
}


def _sanitize_paths(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(str(PROJECT_ROOT), "<PROJECT_ROOT>")
    if isinstance(value, list):
        return [_sanitize_paths(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_paths(item) for key, item in value.items()}
    return value


def _sanitize_tree(case_dir: Path) -> None:
    for path in case_dir.rglob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps(_sanitize_paths(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    for path in case_dir.rglob("*.md"):
        path.write_text(_sanitize_paths(path.read_text(encoding="utf-8")), encoding="utf-8")


def _write_case_readme(case_dir: Path, case_id: str, result: Any) -> None:
    annotation = ANNOTATIONS.get(case_id, {})
    lines = [
        f"# Challenge Case: {case_id}",
        "",
        "This is a synthetic challenge fixture used to stress a specific edge case.",
        "",
        f"- Run id: `{result.run_id}`",
        f"- Profile: `{result.profile}`",
        f"- Quality: `{result.quality.get('status')}` ({result.quality.get('score')}/100)",
        f"- Recovery executed: `{str(result.recovery_decision.get('executed')).lower()}`",
        f"- Selected attempt: `{result.recovery_decision.get('selected_attempt')}`",
        f"- Retrieval chunks: {result.retrieval_export.get('stats', {}).get('total_chunks')}",
        "",
        "## Human Labels",
        "",
    ]
    for key, value in annotation.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "Boundary: labels are sample-level human annotations for this fixture, not an OCR or field-level benchmark on external customer data.",
            "",
        ]
    )
    (case_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def _write_index(results: list[tuple[str, Any]]) -> None:
    rows = [
        "# Challenge Case Human Annotation Table",
        "",
        "These four fixtures add more adversarial and realistic document shapes to the submission evidence.",
        "They are synthetic and public-submission-safe; they are not external customer data.",
        "",
        "| Case | Main Challenge | Human Labels | Quality | Recovery |",
        "| --- | --- | --- | --- | --- |",
    ]
    challenge = {
        "case_6_cross_page_financial_table": "cross-page-style financial subtotal and total",
        "case_7_noisy_contract_scan": "OCR noise and cleanup recovery",
        "case_8_industry_standard_matrix": "industry standard compliance matrix",
        "case_9_incident_workflow_report": "workflow recovery evidence and timeline",
    }
    for case_id, result in results:
        labels = "; ".join(f"{key}={value}" for key, value in ANNOTATIONS.get(case_id, {}).items())
        rows.append(
            "| {case} | {challenge} | {labels} | {quality} ({score}/100) | executed={executed}, selected={selected} |".format(
                case=case_id,
                challenge=challenge.get(case_id, ""),
                labels=labels,
                quality=result.quality.get("status"),
                score=result.quality.get("score"),
                executed=str(result.recovery_decision.get("executed")).lower(),
                selected=result.recovery_decision.get("selected_attempt"),
            )
        )
    rows.append("")
    (DEST_ROOT / "human_annotation_table.md").write_text("\n".join(rows), encoding="utf-8")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    if DEST_ROOT.exists():
        shutil.rmtree(DEST_ROOT)
    DEST_ROOT.mkdir(parents=True, exist_ok=True)

    results = []
    for item in manifest["tasks"]:
        case_id = item["id"]
        input_path = (PROJECT_ROOT / item["input"]).resolve()
        result = MinerUDataAgent().run(
            input_path,
            RUN_ROOT,
            task=item["task"],
            profile=item.get("profile", "auto"),
        )
        case_dir = DEST_ROOT / case_id
        shutil.copytree(Path(result.output_dir), case_dir)
        shutil.copy2(input_path, case_dir / f"input{input_path.suffix}")
        _sanitize_tree(case_dir)
        _write_case_readme(case_dir, case_id, result)
        results.append((case_id, result))

    _write_index(results)
    (DEST_ROOT / "README.md").write_text(
        "# Challenge Case Artifacts\n\n"
        "Generated by `scripts/run_challenge_cases.py` from `examples/challenge_manifest.json`.\n"
        "Each case contains input, result.json, trace.json, summary.md, retrieval exports, and sample-level human labels.\n",
        encoding="utf-8",
    )
    print(json.dumps({"cases": [case_id for case_id, _ in results], "dest": str(DEST_ROOT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
