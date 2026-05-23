from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from mineru_data_agent.agent import MinerUDataAgent
from mineru_data_agent.mineru_client import MinerUAgentAPIRunner


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "examples" / "public_real_documents" / "manifest.json"
FILES_ROOT = PROJECT_ROOT / "examples" / "public_real_documents" / "files"
RUN_ROOT = PROJECT_ROOT / "runs" / "public_real_cases"
DEST_ROOT = PROJECT_ROOT / "submission_artifacts" / "public_real_cases"


class PageRangeAgentAPIRunner:
    def __init__(self, runner: MinerUAgentAPIRunner, page_range: str | None) -> None:
        self.runner = runner
        self.page_range = page_range

    def parse(self, input_path: Path, output_dir: Path, **kwargs: Any):
        start_page, end_page = _parse_page_range(self.page_range)
        return self.runner.parse(input_path, output_dir, start_page=start_page, end_page=end_page, **kwargs)


def _download(url: str, path: Path) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "mineru-data-agent public evidence pack"})
    with urlopen(request, timeout=120) as response:
        path.write_bytes(response.read())


def _parse_page_range(value: str | None) -> tuple[int | None, int | None]:
    if not value:
        return None, None
    if "-" in value:
        left, right = value.split("-", 1)
        return int(left), int(right)
    page = int(value)
    return page, page


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


def _write_case_metadata(case_dir: Path, item: dict[str, Any], result: Any, input_path: Path) -> None:
    metadata = {
        "id": item["id"],
        "source_url": item["source_url"],
        "source_organization": item["source_organization"],
        "source_type": item["source_type"],
        "filename": item["filename"],
        "input_copy": f"input{input_path.suffix.lower()}",
        "task": item["task"],
        "profile": item["profile"],
        "public_document_boundary": (
            "Official public document used for lightweight external-generalization evidence; "
            "not a full OCR character-level benchmark."
        ),
    }
    if item.get("page_range"):
        metadata["page_range"] = item["page_range"]
        metadata["page_range_boundary"] = "Only the listed page range is submitted because of the online MinerU Agent API page limit."
    (case_dir / "source_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    labels = {
        "id": item["id"],
        "human_labels": item["human_labels"],
        "expected_text_contains": item["expected_text_contains"],
        "label_scope": "Sample-level public-document labels for key facts and text evidence.",
    }
    (case_dir / "human_labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    (case_dir / "README.md").write_text(
        "\n".join(
            [
                f"# Public Real Case: {item['id']}",
                "",
                f"- Source: {item['source_url']}",
                f"- Source organization: {item['source_organization']}",
                f"- Source type: {item['source_type']}",
                f"- Profile: `{result.profile}`",
                f"- Quality: `{result.quality.get('status')}` ({result.quality.get('score')}/100)",
                f"- Retrieval chunks: {result.retrieval_export.get('stats', {}).get('total_chunks')}",
                f"- Provenance level: `{result.extracted.get('content_summary', {}).get('provenance_level')}`",
                "",
                "## Human Labels",
                "",
                *[f"- {key}: {value}" for key, value in item["human_labels"].items()],
                "",
                "## Expected Text Evidence",
                "",
                *[f"- {text}" for text in item["expected_text_contains"]],
                "",
                "Boundary: this case uses an official public source and lightweight human labels. "
                "It does not claim full OCR character-level accuracy.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_index(results: list[tuple[dict[str, Any], Any]]) -> None:
    rows = [
        "# Public Real Document Human Annotation Table",
        "",
        "These cases use official public documents to complement synthetic fixtures and challenge cases.",
        "They are intended to test external generalization at a lightweight, sample-labeled level.",
        "",
        "| Case | Public Source | Type | Labels | Quality | Chunks |",
        "| --- | --- | --- | --- | --- | ---: |",
    ]
    artifact_index = []
    for item, result in results:
        labels = "; ".join(f"{key}={value}" for key, value in item["human_labels"].items())
        rows.append(
            "| {case} | {org} | {source_type} | {labels} | {quality} ({score}/100) | {chunks} |".format(
                case=item["id"],
                org=item["source_organization"],
                source_type=item["source_type"],
                labels=labels,
                quality=result.quality.get("status"),
                score=result.quality.get("score"),
                chunks=result.retrieval_export.get("stats", {}).get("total_chunks"),
            )
        )
        artifact_index.append(
            {
                "id": item["id"],
                "source_url": item["source_url"],
                "result_path": f"submission_artifacts/public_real_cases/{item['id']}/result.json",
                "trace_path": f"submission_artifacts/public_real_cases/{item['id']}/trace.json",
                "human_labels_path": f"submission_artifacts/public_real_cases/{item['id']}/human_labels.json",
                "source_metadata_path": f"submission_artifacts/public_real_cases/{item['id']}/source_metadata.json",
            }
        )
    rows.append("")
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    (DEST_ROOT / "human_annotation_table.md").write_text("\n".join(rows), encoding="utf-8")
    (DEST_ROOT / "artifact_index.json").write_text(
        json.dumps({"cases": artifact_index}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (DEST_ROOT / "README.md").write_text(
        "# Public Real Document Artifacts\n\n"
        "Generated by `scripts/run_public_real_cases.py` from `examples/public_real_documents/manifest.json`.\n"
        "Each case contains the official input copy, source metadata, human labels, result.json, trace.json, summary.md, and retrieval exports.\n\n"
        "Scope: these are official public documents used for lightweight external-generalization evidence. "
        "The labels check key facts and text evidence, not full OCR character accuracy or table-cell accuracy. "
        "Long PDFs may declare a `page_range` in source metadata when the online MinerU Agent API page limit applies.\n",
        encoding="utf-8",
    )


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    FILES_ROOT.mkdir(parents=True, exist_ok=True)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    if DEST_ROOT.exists():
        shutil.rmtree(DEST_ROOT)
    DEST_ROOT.mkdir(parents=True, exist_ok=True)

    results = []
    for item in manifest["documents"]:
        input_path = FILES_ROOT / item["filename"]
        _download(item["source_url"], input_path)
        suffix = input_path.suffix.lower()
        if suffix == ".pdf":
            runner = PageRangeAgentAPIRunner(
                MinerUAgentAPIRunner(timeout_seconds=360, poll_interval_seconds=2.0, max_retries=2),
                item.get("page_range"),
            )
            agent = MinerUDataAgent(runner)
        else:
            agent = MinerUDataAgent()
        result = agent.run(
            input_path,
            RUN_ROOT,
            task=item["task"],
            profile=item["profile"],
            method="auto",
            lang="en",
        )
        case_dir = DEST_ROOT / item["id"]
        shutil.copytree(Path(result.output_dir), case_dir)
        shutil.copy2(input_path, case_dir / f"input{suffix}")
        _write_case_metadata(case_dir, item, result, input_path)
        _sanitize_tree(case_dir)
        results.append((item, result))

    _write_index(results)
    print(json.dumps({"cases": [item["id"] for item, _ in results], "dest": str(DEST_ROOT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
