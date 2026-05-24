from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import MinerUDataAgent
from .agent_live import DEFAULT_MAX_TOKENS, DEFAULT_MAX_TURNS, DEFAULT_TIMEOUT, live_trace_to_jsonable, run_live_agent
from .batch import run_batch
from .llm_client import DeepSeekLLMClient, ModelScopeLLMClient
from .mineru_client import MinerUAgentAPIRunner, MinerURunner, resolve_mineru_executable


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the MinerU Data Agent.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Parse one document and produce structured output.")
    run.add_argument("--input", required=True, help="Input PDF/image/office/html file.")
    run.add_argument("--out", default="runs", help="Output directory.")
    run.add_argument("--task", required=True, help="Natural-language task objective.")
    run.add_argument("--profile", default="auto", help="auto, financial_report, standard_or_contract, workflow_or_diagram, low_quality_ocr.")
    run.add_argument("--backend", default="pipeline", help="MinerU backend, default: pipeline.")
    run.add_argument("--method", default="auto", help="MinerU parse method, default: auto.")
    run.add_argument("--lang", default="ch", help="OCR language hint.")
    run.add_argument("--runner", choices=["cli", "agent-api"], default="cli", help="Use local MinerU CLI or MinerU online Agent API.")
    run.add_argument("--mineru-executable", default=None, help="Path to mineru executable.")
    run.add_argument("--api-timeout", type=int, default=300, help="Online API task timeout in seconds.")
    run.add_argument("--api-poll-interval", type=float, default=3.0, help="Online API polling interval in seconds.")
    run.add_argument("--api-max-retries", type=int, default=2, help="Retry transient online API failures.")
    run.add_argument(
        "--no-cli-fallback-on-no-page-provenance",
        dest="cli_fallback_on_no_page_provenance",
        action="store_false",
        default=True,
        help="Disable automatic local MinerU CLI fallback when the online API lacks page provenance.",
    )
    run.add_argument(
        "--strict-page-provenance",
        action="store_true",
        help="Mark PDF/image results as needs_review if page-level provenance is still missing after recovery.",
    )
    run.add_argument("--fallback-mineru-executable", default=None, help="Path to mineru executable for CLI fallback.")
    _add_llm_args(run)

    batch = subparsers.add_parser("batch", help="Run multiple tasks from a JSON manifest and write a batch report.")
    batch.add_argument("--manifest", required=True, help="JSON manifest with a tasks list.")
    batch.add_argument("--out", default="runs/batch", help="Output directory.")
    batch.add_argument("--backend", default="pipeline", help="Default MinerU backend.")
    batch.add_argument("--method", default="auto", help="Default parse method.")
    batch.add_argument("--lang", default="ch", help="Default OCR language hint.")
    batch.add_argument("--profile", default="auto", help="Default task profile.")
    batch.add_argument("--runner", choices=["cli", "agent-api"], default="cli", help="Use local MinerU CLI or MinerU online Agent API.")
    batch.add_argument("--mineru-executable", default=None, help="Path to mineru executable.")
    batch.add_argument("--api-timeout", type=int, default=300, help="Online API task timeout in seconds.")
    batch.add_argument("--api-poll-interval", type=float, default=3.0, help="Online API polling interval in seconds.")
    batch.add_argument("--api-max-retries", type=int, default=2, help="Retry transient online API failures.")
    batch.add_argument(
        "--no-cli-fallback-on-no-page-provenance",
        dest="cli_fallback_on_no_page_provenance",
        action="store_false",
        default=True,
        help="Disable automatic local MinerU CLI fallback when the online API lacks page provenance.",
    )
    batch.add_argument(
        "--strict-page-provenance",
        action="store_true",
        help="Mark PDF/image results as needs_review if page-level provenance is still missing after recovery.",
    )
    batch.add_argument("--fallback-mineru-executable", default=None, help="Path to mineru executable for CLI fallback.")
    _add_llm_args(batch)

    agent_run = subparsers.add_parser("agent-run", help="Run the live LLM tool-calling Agent path.")
    agent_run.add_argument("--input", required=True, help="Input PDF/office/html file.")
    agent_run.add_argument("--out", default="runs/agent_live", help="Output directory.")
    agent_run.add_argument("--task", required=True, help="Natural-language task objective.")
    agent_run.add_argument("--provider", choices=["deepseek", "modelscope"], default="modelscope", help="Live LLM provider; API key is read from environment only.")
    agent_run.add_argument("--model", default=None, help="Model name. Defaults to provider environment/config.")
    agent_run.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS, help="Maximum live-agent tool turns.")
    agent_run.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="Maximum completion tokens per LLM turn.")
    agent_run.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="LLM request timeout in seconds.")
    agent_run.add_argument("--mineru-executable", default=None, help="Optional local MinerU executable for PDF parse tools.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command in {"run", "batch"}:
        runner = _build_runner(args)
        agent = MinerUDataAgent(
            runner,
            llm_client=_build_llm_client(args),
            fallback_mineru_runner=_build_fallback_runner(args),
        )
    if args.command == "run":
        result = agent.run(
            Path(args.input),
            Path(args.out),
            task=args.task,
            profile=args.profile,
            backend=args.backend,
            method=args.method,
            lang=args.lang,
            strict_page_provenance=args.strict_page_provenance,
        )
        print(json.dumps(result.to_jsonable(), ensure_ascii=False, indent=2))
    elif args.command == "batch":
        report = run_batch(
            manifest_path=Path(args.manifest),
            output_root=Path(args.out),
            agent=agent,
            defaults={
                "profile": args.profile,
                "backend": args.backend,
                "method": args.method,
                "lang": args.lang,
                "strict_page_provenance": args.strict_page_provenance,
            },
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.command == "agent-run":
        _validate_live_agent_limits(args.max_turns, args.max_tokens, args.timeout)
        trace = run_live_agent(
            input_file=Path(args.input),
            output_root=Path(args.out),
            task=args.task,
            provider=args.provider,
            model=args.model,
            max_turns=args.max_turns,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
            mineru_runner=MinerURunner(executable=args.mineru_executable) if args.mineru_executable else None,
        )
        print(json.dumps(live_trace_to_jsonable(trace, display_paths=True), ensure_ascii=False, indent=2))


def _validate_live_agent_limits(max_turns: int, max_tokens: int, timeout: float) -> None:
    if max_turns < 1 or max_turns > 30:
        raise SystemExit("--max-turns must be in range 1..30")
    if max_tokens < 1 or max_tokens > 4096:
        raise SystemExit("--max-tokens must be in range 1..4096")
    if timeout <= 0 or timeout > 600:
        raise SystemExit("--timeout must be in range 0..600")


def _build_runner(args: argparse.Namespace) -> MinerURunner | MinerUAgentAPIRunner:
    if args.runner == "agent-api":
        return MinerUAgentAPIRunner(
            timeout_seconds=args.api_timeout,
            poll_interval_seconds=args.api_poll_interval,
            max_retries=args.api_max_retries,
        )
    return MinerURunner(executable=args.mineru_executable)


def _build_fallback_runner(args: argparse.Namespace) -> MinerURunner | None:
    if args.runner != "agent-api" or not args.cli_fallback_on_no_page_provenance:
        return None
    executable = resolve_mineru_executable(args.fallback_mineru_executable or args.mineru_executable)
    if not executable:
        return None
    return MinerURunner(executable=executable)


def _add_llm_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--llm", choices=["none", "deepseek", "modelscope"], default="none", help="Optional LLM reasoning layer.")
    parser.add_argument("--llm-model", default=None, help="LLM model name.")
    parser.add_argument("--llm-base-url", default=None, help="OpenAI-compatible base URL.")
    parser.add_argument("--llm-timeout", type=float, default=60.0, help="LLM request timeout in seconds.")
    parser.add_argument("--llm-max-preview-chars", type=int, default=4000, help="Markdown preview characters sent to LLM.")


def _build_llm_client(args: argparse.Namespace) -> DeepSeekLLMClient | ModelScopeLLMClient | None:
    if args.llm == "none":
        return None
    if args.llm == "modelscope":
        return ModelScopeLLMClient(
            model=args.llm_model,
            base_url=args.llm_base_url,
            timeout_seconds=args.llm_timeout,
            max_preview_chars=args.llm_max_preview_chars,
        )
    return DeepSeekLLMClient(
        model=args.llm_model,
        base_url=args.llm_base_url,
        timeout_seconds=args.llm_timeout,
        max_preview_chars=args.llm_max_preview_chars,
    )


if __name__ == "__main__":
    main()
