from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from mineru_data_agent.agent import MinerUDataAgent
from mineru_data_agent.mineru_client import MinerUAgentAPIRunner
from mineru_data_agent.models import ParseArtifacts, ToolCall


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PDF = PROJECT_ROOT / "examples" / "real_pdfs" / "standard_contract_cross_page.pdf"
OUTPUT_ROOT = PROJECT_ROOT / "runs" / "recovery_evidence"
DEST_ROOT = PROJECT_ROOT / "submission_artifacts" / "recovery_cases" / "case_pdf_llm_api_to_cli_fallback"
CACHED_CLI_CASE = PROJECT_ROOT / "submission_artifacts" / "mineru_cases" / "case_mineru_cli_contract_pdf"


class OfflinePreplanningLLM:
    """Deterministic preplanning client used only when external LLM keys are unavailable."""

    def plan_execution(self, **kwargs: Any) -> tuple[dict[str, Any], ToolCall]:
        return (
            {
                "enabled": True,
                "status": "completed",
                "task_understanding": "Contract PDF requires structured clause/table extraction and page-level auditability.",
                "recommended_profile": "standard_or_contract",
                "recommended_runner": "cli",
                "recommended_backend": "pipeline",
                "recommended_method": "auto",
                "recommended_lang": "en",
                "execution_plan": [
                    "Use online Agent API as the first low-cost parser.",
                    "Validate page-level provenance before accepting the result.",
                    "Fallback to local MinerU CLI if page provenance is missing.",
                    "Build structured JSON, retrieval chunks, and trace evidence.",
                ],
                "target_schema": {
                    "Contract No": "contract identifier",
                    "Effective Date": "contract effective date",
                    "Clause": "compliance clause id",
                    "Evidence Field": "traceable output field",
                },
                "verification_focus": [
                    "page provenance",
                    "table chunk preservation",
                    "recovery attempt selection",
                ],
                "recovery_policy": [
                    "If no_page_provenance appears after online API parsing, fallback to local CLI artifacts.",
                ],
                "confidence": 0.88,
                "boundary": "offline deterministic scheduler; set DEEPSEEK_API_KEY or MODELSCOPE_API_KEY for live LLM.",
            },
            ToolCall(
                tool="offline-llm-preplan",
                command=["offline-preplanner", "standard_contract_cross_page.pdf"],
                status="completed",
                elapsed_seconds=0.001,
            ),
        )

    def analyze(self, **kwargs: Any) -> tuple[dict[str, Any], ToolCall]:
        return (
            {
                "status": "completed",
                "task_understanding": "Fallback selected the page-level CLI artifact after online API provenance warning.",
                "execution_plan": ["Review selected attempt and retrieval chunks."],
                "target_schema": {
                    "Contract No": "contract identifier",
                    "Effective Date": "contract effective date",
                    "Signed by": "signature parties",
                },
                "verification_focus": ["recovery_decision.executed", "selected_attempt", "trace tool calls"],
                "risk_findings": [
                    {
                        "level": "info",
                        "message": "Live external LLM was not used in this environment.",
                        "evidence": "offline-llm-preplan tool call in trace",
                    }
                ],
                "recovery_suggestions": ["Re-run with live ModelScope or DeepSeek key before final live-demo submission."],
            },
            ToolCall(
                tool="offline-llm",
                command=["offline-preplanner", "post-parse-review"],
                status="completed",
                elapsed_seconds=0.001,
            ),
        )


class CachedCLIFallbackRunner:
    """Replay saved local MinerU CLI artifacts as a fallback evidence drill."""

    def parse(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
    ) -> tuple[ParseArtifacts, ToolCall]:
        source = CACHED_CLI_CASE / "mineru" / "standard_contract_cross_page" / "auto"
        if not source.exists():
            raise FileNotFoundError(f"Cached CLI artifact is missing: {source}")
        base = output_dir / input_path.stem / "auto"
        if base.exists():
            shutil.rmtree(base)
        shutil.copytree(source, base)

        def first(pattern: str) -> Path | None:
            matches = sorted(base.glob(pattern))
            return matches[0] if matches else None

        return (
            ParseArtifacts(
                markdown_path=first("*.md"),
                content_list_path=first("*content_list.json"),
                middle_json_path=first("*middle.json"),
                model_json_path=first("*model.json"),
                layout_pdf_path=first("*layout.pdf"),
                span_pdf_path=first("*span.pdf"),
                origin_pdf_path=first("*origin.pdf"),
                image_dir=(base / "images") if (base / "images").exists() else None,
            ),
            ToolCall(
                tool="cached-mineru-cli-fallback",
                command=["cached-mineru-cli", str(source), "->", str(base)],
                status="completed",
                elapsed_seconds=0.001,
            ),
        )


def _sanitize_paths(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(str(PROJECT_ROOT), "<PROJECT_ROOT>")
    if isinstance(value, list):
        return [_sanitize_paths(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_paths(item) for key, item in value.items()}
    return value


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    DEST_ROOT.parent.mkdir(parents=True, exist_ok=True)
    if DEST_ROOT.exists():
        shutil.rmtree(DEST_ROOT)

    agent = MinerUDataAgent(
        MinerUAgentAPIRunner(timeout_seconds=300, poll_interval_seconds=2.0, max_retries=2),
        llm_client=OfflinePreplanningLLM(),
        fallback_mineru_runner=CachedCLIFallbackRunner(),
    )
    result = agent.run(
        INPUT_PDF,
        OUTPUT_ROOT,
        task=(
            "Parse the contract PDF, let the LLM preplanner define schema and recovery policy, "
            "use online API first, and automatically fallback to local CLI when page provenance is missing."
        ),
        profile="auto",
        method="auto",
        lang="ch",
    )

    shutil.copytree(Path(result.output_dir), DEST_ROOT)
    shutil.copy2(INPUT_PDF, DEST_ROOT / "input.pdf")
    for path in [DEST_ROOT / "result.json", DEST_ROOT / "trace.json", DEST_ROOT / "summary.md"]:
        if path.exists():
            if path.suffix == ".json":
                payload = json.loads(path.read_text(encoding="utf-8"))
                path.write_text(json.dumps(_sanitize_paths(payload), ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                path.write_text(_sanitize_paths(path.read_text(encoding="utf-8")), encoding="utf-8")

    for path in (DEST_ROOT / "retrieval").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps(_sanitize_paths(payload), ensure_ascii=False, indent=2), encoding="utf-8")

    (DEST_ROOT / "README.md").write_text(
        "\n".join(
            [
                "# PDF LLM Preplan + API-to-CLI Fallback Evidence",
                "",
                "This case uses a real PDF fixture as input and runs the production Agent recovery path.",
                "",
                "- Input: `examples/real_pdfs/standard_contract_cross_page.pdf`",
                "- Initial parser: MinerU online Agent API",
                "- Recovery trigger: `no_page_provenance`",
                "- Fallback parser: cached local MinerU CLI artifact from `case_mineru_cli_contract_pdf`",
                "- LLM preplanning: offline deterministic scheduler because no external LLM key is present in this environment",
                f"- Run id: `{result.run_id}`",
                f"- Quality: `{result.quality.get('status')}` ({result.quality.get('score')}/100)",
                f"- Recovery executed: `{str(result.recovery_decision.get('executed')).lower()}`",
                f"- Selected attempt: `{result.recovery_decision.get('selected_attempt')}`",
                "",
                "Boundary: this is a recovery evidence drill. It proves code-level automatic fallback and attempt selection. "
                "For a live LLM/CLI evidence run, set `MODELSCOPE_API_KEY` or `DEEPSEEK_API_KEY` and provide a real `mineru` executable.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({"run_id": result.run_id, "dest": str(DEST_ROOT), "selected_attempt": result.recovery_decision.get("selected_attempt")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
