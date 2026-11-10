from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .agent import MinerUDataAgent
from .agent_live import DEFAULT_MAX_TOKENS, DEFAULT_MAX_TURNS, DEFAULT_TIMEOUT, live_trace_to_jsonable, run_live_agent
from .batch import run_batch
from .corpus import build_corpus_catalog, load_document_reference, search_corpus_catalog
from .interactive import run_interactive_chat
from .llm_client import DeepSeekLLMClient, ModelScopeLLMClient
from .mineru_client import MinerUAgentAPIRunner, MinerUPreciseAPIRunner, MinerURunner, resolve_mineru_executable
from .source_packager import build_source_document_packages


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
    run.add_argument(
        "--runner",
        choices=["auto", "cli", "agent-api", "precise-api"],
        default="cli",
        help="Choose parser runner. auto lets the workflow router pick native/Agent API/precise API/CLI.",
    )
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
    batch.add_argument(
        "--runner",
        choices=["auto", "cli", "agent-api", "precise-api"],
        default="cli",
        help="Choose parser runner. auto lets the workflow router pick native/Agent API/precise API/CLI.",
    )
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

    chat = subparsers.add_parser("chat", help="Start an interactive natural-language Data Agent harness.")
    chat.add_argument("--out", default="runs/chat", help="Output directory for interactive runs.")
    chat.add_argument("--provider", choices=["deepseek"], default="deepseek", help="Planner provider for natural-language commands.")
    chat.add_argument("--model", default=None, help="Planner model. Defaults to DEEPSEEK_MODEL or deepseek-v4-flash.")
    chat.add_argument("--dry-run", action="store_true", help="Plan interactively without executing document parsing.")
    chat.add_argument(
        "--mode",
        choices=["live", "classic"],
        default="live",
        help="Execution mode. live uses the LLM tool-calling workflow; classic uses the deterministic run pipeline.",
    )
    chat.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS, help="Maximum live-agent tool turns.")
    chat.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="Maximum completion tokens per LLM turn.")
    chat.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Live-agent LLM request timeout in seconds.")
    chat.add_argument("--mineru-executable", default=None, help="Optional local MinerU executable for PDF parse tools.")

    corpus = subparsers.add_parser("corpus", help="Build/search/load a progressive-disclosure corpus catalog.")
    corpus_sub = corpus.add_subparsers(dest="corpus_command", required=True)
    corpus_build = corpus_sub.add_parser("build", help="Scan document_skill packages and write a corpus catalog.")
    corpus_build.add_argument("--root", required=True, help="Directory containing document_skill packages.")
    corpus_build.add_argument("--out", default=None, help="Catalog output directory. Defaults to --root.")
    corpus_package = corpus_sub.add_parser(
        "package-sources",
        help="Reorganize run/chunk outputs into one document_skill package per original source document.",
    )
    corpus_package.add_argument("--run-root", required=True, help="Run directory containing result.json files, batch reports, and optional chunk plan.")
    corpus_package.add_argument("--source-root", default=None, help="Original source folder. If omitted, infer from manifests/results.")
    corpus_package.add_argument("--out", default=None, help="Output directory. Defaults to runs/YYYYMMDDHHMM next to --run-root.")
    corpus_search = corpus_sub.add_parser("search", help="Search a corpus catalog by name/description.")
    corpus_search.add_argument("--catalog", required=True, help="Path to corpus_catalog.json or corpus_catalog.jsonl.")
    corpus_search.add_argument("--query", required=True, help="Search query.")
    corpus_search.add_argument("--limit", type=int, default=10, help="Maximum results.")
    corpus_load = corpus_sub.add_parser("load", help="Load one reference from a document_skill package on demand.")
    corpus_load.add_argument("--package-dir", required=True, help="Path to one document_skill package.")
    corpus_load.add_argument(
        "--reference",
        default="compressed",
        choices=["skill", "overview", "compressed", "content", "structured", "tables", "evidence", "segments", "raw_result", "retrieval_chunks"],
        help="Reference file to load.",
    )
    corpus_load.add_argument("--max-chars", type=int, default=12000, help="Maximum characters to return.")
    return parser


def main() -> None:
    _configure_stdout()
    _load_project_env()
    args = build_parser().parse_args()
    if args.command in {"run", "batch"}:
        runner = _build_runner(args)
        agent = MinerUDataAgent(
            runner,
            llm_client=_build_llm_client(args),
            fallback_mineru_runner=_build_fallback_runner(args),
            requested_runner=args.runner,
            auto_runner=args.runner == "auto",
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
        _print_json(result.to_jsonable())
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
        _print_json(report)
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
        _print_json(live_trace_to_jsonable(trace, display_paths=True))
    elif args.command == "chat":
        _validate_live_agent_limits(args.max_turns, args.max_tokens, args.timeout)
        _require_chat_keys(args.provider, dry_run=args.dry_run)
        run_interactive_chat(
            output_root=Path(args.out),
            provider=args.provider,
            model=args.model,
            dry_run=args.dry_run,
            execution_mode=args.mode,
            max_turns=args.max_turns,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
            mineru_executable=args.mineru_executable,
        )
    elif args.command == "corpus":
        if args.corpus_command == "build":
            payload = build_corpus_catalog(
                root=Path(args.root),
                output_dir=Path(args.out) if args.out else None,
            )
            _print_json(payload)
        elif args.corpus_command == "package-sources":
            _print_json(
                build_source_document_packages(
                    run_root=Path(args.run_root),
                    source_root=Path(args.source_root) if args.source_root else None,
                    output_root=Path(args.out) if args.out else None,
                )
            )
        elif args.corpus_command == "search":
            _print_json(search_corpus_catalog(catalog_path=Path(args.catalog), query=args.query, limit=args.limit))
        elif args.corpus_command == "load":
            _print_json(
                load_document_reference(
                    package_dir=Path(args.package_dir),
                    reference=args.reference,
                    max_chars=args.max_chars,
                )
            )


def _validate_live_agent_limits(max_turns: int, max_tokens: int, timeout: float) -> None:
    if max_turns < 1 or max_turns > 30:
        raise SystemExit("--max-turns must be in range 1..30")
    if max_tokens < 1 or max_tokens > 4096:
        raise SystemExit("--max-tokens must be in range 1..4096")
    if timeout <= 0 or timeout > 600:
        raise SystemExit("--timeout must be in range 0..600")


def _require_chat_keys(provider: str, *, dry_run: bool) -> None:
    """The LLM is the agent's brain, so `chat` needs an LLM key (except in dry-run).

    The MinerU token is intentionally NOT required: routing can pick the
    token-free Agent API or native extractors for many documents.
    """
    if dry_run:
        return
    key_env = "DEEPSEEK_API_KEY" if provider == "deepseek" else "MODELSCOPE_API_KEY"
    if not os.getenv(key_env):
        raise SystemExit(
            f"{key_env} is required for `data-agent chat` (the LLM drives the agent). "
            "Set it in your environment or .env file. "
            "Tip: a MinerU token is optional — it is only needed when the precise API is selected."
        )


def _configure_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _build_runner(args: argparse.Namespace) -> MinerURunner | MinerUAgentAPIRunner | MinerUPreciseAPIRunner:
    if args.runner == "auto":
        return MinerURunner(executable=args.mineru_executable)
    if args.runner == "agent-api":
        return MinerUAgentAPIRunner(
            timeout_seconds=args.api_timeout,
            poll_interval_seconds=args.api_poll_interval,
            max_retries=args.api_max_retries,
        )
    if args.runner == "precise-api":
        return MinerUPreciseAPIRunner(
            timeout_seconds=args.api_timeout,
            poll_interval_seconds=args.api_poll_interval,
            max_retries=args.api_max_retries,
        )
    return MinerURunner(executable=args.mineru_executable)


def _build_fallback_runner(args: argparse.Namespace) -> MinerURunner | None:
    if args.runner not in {"agent-api", "auto"} or not args.cli_fallback_on_no_page_provenance:
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


def _load_project_env(start: Path | None = None) -> Path | None:
    root = (start or Path.cwd()).resolve()
    candidates = [root, *root.parents]
    for directory in candidates:
        env_path = directory / ".env"
        if env_path.exists():
            _load_env_file(env_path)
            return env_path
    return None


def _load_env_file(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


if __name__ == "__main__":
    main()
