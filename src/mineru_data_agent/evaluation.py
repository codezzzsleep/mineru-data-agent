from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def evaluate_cases(labels_path: Path, *, project_root: Path | None = None) -> dict[str, Any]:
    project_root = (project_root or Path.cwd()).resolve()
    labels_path = labels_path.expanduser().resolve()
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    raw_cases = labels.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("Evaluation labels must contain a non-empty 'cases' list.")

    case_reports = [_evaluate_case(raw_case, project_root) for raw_case in raw_cases]
    totals = _aggregate(case_reports)
    return {
        "schema_version": "2026-05-23",
        "labels_path": _display_path(labels_path, project_root),
        "project_root": "<PROJECT_ROOT>",
        "case_count": len(case_reports),
        "aggregate": totals,
        "cases": case_reports,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# Evaluation Metrics",
        "",
        "This report compares saved submission artifacts against lightweight human labels.",
        "",
        "## Aggregate",
        "",
        f"- Cases: {report['case_count']}",
        f"- Expected-field accuracy: {_pct(aggregate['field_accuracy'])} "
        f"({aggregate['matched_fields']}/{aggregate['expected_fields']})",
        f"- Profile accuracy: {_pct(aggregate['profile_accuracy'])} "
        f"({aggregate['profile_matches']}/{aggregate['profile_checks']})",
        f"- Structure gate pass rate: {_pct(aggregate['structure_gate_pass_rate'])} "
        f"({aggregate['structure_gates_passed']}/{aggregate['structure_gates']})",
        f"- Quality gate pass rate: {_pct(aggregate['quality_gate_pass_rate'])} "
        f"({aggregate['quality_gates_passed']}/{aggregate['quality_gates']})",
        f"- Provenance gate pass rate: {_pct(aggregate['provenance_gate_pass_rate'])} "
        f"({aggregate['provenance_gates_passed']}/{aggregate['provenance_gates']})",
        f"- Recovery gate pass rate: {_pct(aggregate['recovery_gate_pass_rate'])} "
        f"({aggregate['recovery_gates_passed']}/{aggregate['recovery_gates']})",
        "",
        "## Cases",
        "",
        "| Case | Field Accuracy | Profile | Structure | Quality | Provenance | Recovery | Result |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["cases"]:
        result_path = item.get("result_path", "")
        lines.append(
            "| {case_id} | {field_accuracy} | {profile} | {structure} | {quality} | {provenance} | {recovery} | `{result}` |".format(
                case_id=item["id"],
                field_accuracy=_pct(item["field_accuracy"]),
                profile=_ok(item["profile_match"]),
                structure=_ok(item["structure_gate"]["passed"]),
                quality=_ok(item["quality_gate"]["passed"]),
                provenance=_ok(item["provenance_gate"]["passed"]),
                recovery=_ok(item["recovery_gate"]["passed"]),
                result=result_path,
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Field accuracy here measures labeled key-value expectations, not full OCR character accuracy.",
            "- Structure gates check minimum sections, tables, numeric facts, retrieval chunks, and issue codes where labels define them.",
            "- Recovery gates check executed recovery decisions, selected attempts, final decisions, and preserved initial issue codes when labels define them.",
            "- This complements the trace/artifact evidence and gives reviewers a reproducible scoring surface.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _evaluate_case(raw_case: Any, project_root: Path) -> dict[str, Any]:
    if not isinstance(raw_case, dict):
        raise ValueError("Each evaluation case must be an object.")
    case_id = str(raw_case.get("id") or "").strip()
    result_path = _resolve_path(raw_case.get("result_path"), project_root)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    extracted = result.get("extracted", {})
    quality = result.get("quality", {})
    retrieval = result.get("retrieval_export", {})
    recovery = result.get("recovery_decision", {})

    field_checks = _check_fields(raw_case.get("expected_fields", {}), extracted.get("key_value_map", {}))
    profile_match = result.get("profile") == raw_case.get("expected_profile")
    structure_gate = _check_structure(raw_case.get("minimums", {}), extracted, retrieval, quality)
    quality_gate = _check_quality(raw_case.get("expected_quality", {}), quality)
    provenance_gate = _check_provenance(raw_case.get("expected_provenance"), extracted)
    recovery_gate = _check_recovery(raw_case.get("expected_recovery"), recovery)
    expected_count = len(field_checks)
    matched_count = sum(1 for item in field_checks if item["matched"])
    return {
        "id": case_id,
        "result_path": _display_path(result_path, project_root),
        "profile": result.get("profile"),
        "expected_profile": raw_case.get("expected_profile"),
        "profile_match": profile_match,
        "field_accuracy": matched_count / expected_count if expected_count else 1.0,
        "matched_fields": matched_count,
        "expected_fields": expected_count,
        "field_checks": field_checks,
        "structure_gate": structure_gate,
        "quality_gate": quality_gate,
        "provenance_gate": provenance_gate,
        "recovery_gate": recovery_gate,
    }


def _check_fields(expected_fields: Any, key_value_map: Any) -> list[dict[str, Any]]:
    if not isinstance(expected_fields, dict):
        return []
    actual_map = key_value_map if isinstance(key_value_map, dict) else {}
    checks = []
    for key, expected in expected_fields.items():
        actual = actual_map.get(key)
        matched = _value_matches(expected, actual)
        checks.append(
            {
                "field": key,
                "expected": expected,
                "actual": actual,
                "matched": matched,
            }
        )
    return checks


def _check_structure(minimums: Any, extracted: dict[str, Any], retrieval: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    minimums = minimums if isinstance(minimums, dict) else {}
    stats = retrieval.get("stats", {}) if isinstance(retrieval.get("stats"), dict) else {}
    actual = {
        "sections": len(extracted.get("sections", [])) if isinstance(extracted.get("sections"), list) else 0,
        "tables": len(extracted.get("tables", [])) if isinstance(extracted.get("tables"), list) else 0,
        "numeric_facts": len(extracted.get("numeric_facts", [])) if isinstance(extracted.get("numeric_facts"), list) else 0,
        "retrieval_chunks": int(stats.get("total_chunks") or 0),
    }
    failures = []
    for key, expected_min in minimums.items():
        if key == "issue_codes":
            continue
        if actual.get(key, 0) < int(expected_min):
            failures.append({"metric": key, "expected_min": expected_min, "actual": actual.get(key, 0)})
    expected_issue_codes = minimums.get("issue_codes")
    if isinstance(expected_issue_codes, list):
        issue_codes = {
            str(item.get("code"))
            for item in quality.get("issues", [])
            if isinstance(item, dict) and item.get("code")
        }
        for code in expected_issue_codes:
            if str(code) not in issue_codes:
                failures.append({"metric": "issue_codes", "expected": code, "actual": sorted(issue_codes)})
    return {"passed": not failures, "actual": actual, "failures": failures}


def _check_quality(expected_quality: Any, quality: dict[str, Any]) -> dict[str, Any]:
    expected_quality = expected_quality if isinstance(expected_quality, dict) else {}
    failures = []
    expected_status = expected_quality.get("status")
    if expected_status and quality.get("status") != expected_status:
        failures.append({"metric": "status", "expected": expected_status, "actual": quality.get("status")})
    min_score = expected_quality.get("min_score")
    if min_score is not None and int(quality.get("score") or 0) < int(min_score):
        failures.append({"metric": "score", "expected_min": min_score, "actual": quality.get("score")})
    return {"passed": not failures, "actual": {"status": quality.get("status"), "score": quality.get("score")}, "failures": failures}


def _check_provenance(expected: Any, extracted: dict[str, Any]) -> dict[str, Any]:
    if not expected:
        return {"passed": True, "expected": None, "actual": None, "failures": []}
    summary = extracted.get("content_summary", {}) if isinstance(extracted.get("content_summary"), dict) else {}
    actual = summary.get("provenance_level")
    failures = [] if actual == expected else [{"metric": "provenance_level", "expected": expected, "actual": actual}]
    return {"passed": not failures, "expected": expected, "actual": actual, "failures": failures}


def _check_recovery(expected: Any, recovery: Any) -> dict[str, Any]:
    if not expected:
        return {"passed": True, "expected": None, "actual": None, "failures": []}
    expected = expected if isinstance(expected, dict) else {}
    recovery = recovery if isinstance(recovery, dict) else {}
    actual = {
        "executed": recovery.get("executed"),
        "selected_attempt": recovery.get("selected_attempt"),
        "decision": recovery.get("decision"),
        "initial_issue_codes": recovery.get("initial_issue_codes") or [],
    }
    failures = []
    for key in ("executed", "selected_attempt", "decision"):
        if key in expected and actual.get(key) != expected.get(key):
            failures.append({"metric": key, "expected": expected.get(key), "actual": actual.get(key)})
    expected_issue_codes = expected.get("initial_issue_codes")
    if isinstance(expected_issue_codes, list):
        actual_issue_codes = {str(code) for code in actual["initial_issue_codes"]}
        for code in expected_issue_codes:
            if str(code) not in actual_issue_codes:
                failures.append(
                    {
                        "metric": "initial_issue_codes",
                        "expected": code,
                        "actual": sorted(actual_issue_codes),
                    }
                )
    return {"passed": not failures, "expected": expected, "actual": actual, "failures": failures}


def _aggregate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    expected_fields = sum(item["expected_fields"] for item in cases)
    matched_fields = sum(item["matched_fields"] for item in cases)
    profile_checks = len(cases)
    profile_matches = sum(1 for item in cases if item["profile_match"])
    structure_gates = len(cases)
    structure_gates_passed = sum(1 for item in cases if item["structure_gate"]["passed"])
    quality_gates = len(cases)
    quality_gates_passed = sum(1 for item in cases if item["quality_gate"]["passed"])
    provenance_gates = sum(1 for item in cases if item["provenance_gate"]["expected"])
    provenance_gates_passed = sum(
        1 for item in cases if item["provenance_gate"]["expected"] and item["provenance_gate"]["passed"]
    )
    recovery_gates = sum(1 for item in cases if item["recovery_gate"]["expected"])
    recovery_gates_passed = sum(
        1 for item in cases if item["recovery_gate"]["expected"] and item["recovery_gate"]["passed"]
    )
    return {
        "expected_fields": expected_fields,
        "matched_fields": matched_fields,
        "field_accuracy": matched_fields / expected_fields if expected_fields else 1.0,
        "profile_checks": profile_checks,
        "profile_matches": profile_matches,
        "profile_accuracy": profile_matches / profile_checks if profile_checks else 1.0,
        "structure_gates": structure_gates,
        "structure_gates_passed": structure_gates_passed,
        "structure_gate_pass_rate": structure_gates_passed / structure_gates if structure_gates else 1.0,
        "quality_gates": quality_gates,
        "quality_gates_passed": quality_gates_passed,
        "quality_gate_pass_rate": quality_gates_passed / quality_gates if quality_gates else 1.0,
        "provenance_gates": provenance_gates,
        "provenance_gates_passed": provenance_gates_passed,
        "provenance_gate_pass_rate": provenance_gates_passed / provenance_gates if provenance_gates else 1.0,
        "recovery_gates": recovery_gates,
        "recovery_gates_passed": recovery_gates_passed,
        "recovery_gate_pass_rate": recovery_gates_passed / recovery_gates if recovery_gates else 1.0,
    }


def _resolve_path(value: Any, project_root: Path) -> Path:
    if not value:
        raise ValueError("Evaluation case is missing result_path.")
    path = Path(str(value))
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _display_path(path: Path, project_root: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _value_matches(expected: Any, actual: Any) -> bool:
    if actual is None:
        return False
    actual_text = _normalize_value(actual)
    if isinstance(expected, dict):
        if "contains" in expected:
            return _normalize_value(expected["contains"]) in actual_text
        if "equals" in expected:
            return actual_text == _normalize_value(expected["equals"])
        if "one_of" in expected and isinstance(expected["one_of"], list):
            return actual_text in {_normalize_value(item) for item in expected["one_of"]}
    return actual_text == _normalize_value(expected)


def _normalize_value(value: Any) -> str:
    return " ".join(str(value).strip().split()).lower()


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _ok(value: bool) -> str:
    return "pass" if value else "fail"
