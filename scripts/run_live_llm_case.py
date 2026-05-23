from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

from mineru_data_agent.agent import MinerUDataAgent
from mineru_data_agent.llm_client import DeepSeekLLMClient, ModelScopeLLMClient
from mineru_data_agent.mineru_client import MinerURunner


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "examples" / "cases" / "case_1_financial_report.html"
RUN_ROOT = PROJECT_ROOT / "runs" / "live_llm_cases"
DEST_ROOT = PROJECT_ROOT / "submission_artifacts" / "llm_cases"


def main() -> None:
    args = parse_args()
    if args.provider == "modelscope" and not os.getenv("MODELSCOPE_API_KEY"):
        raise SystemExit("MODELSCOPE_API_KEY is required for --provider modelscope")
    if args.provider == "deepseek" and not os.getenv("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required for --provider deepseek")

    input_path = Path(args.input).resolve()
    run_root = Path(args.run_root).resolve()
    case_dir = Path(args.output_dir).resolve() / args.case_id
    run_root.mkdir(parents=True, exist_ok=True)
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.parent.mkdir(parents=True, exist_ok=True)

    llm_client = build_llm_client(args)
    agent = MinerUDataAgent(MinerURunner(), llm_client=llm_client)
    result = agent.run(
        input_path,
        run_root,
        task=args.task,
        profile=args.profile,
        method=args.method,
        lang=args.lang,
    )
    shutil.copytree(Path(result.output_dir), case_dir)
    shutil.copy2(input_path, case_dir / f"input{input_path.suffix.lower()}")
    write_readme(case_dir, args, result)
    sanitize_tree(case_dir)
    print(
        json.dumps(
            {
                "case_dir": display_path(case_dir),
                "provider": args.provider,
                "model": args.model,
                "run_id": result.run_id,
                "llm_usage_summary": result.llm_analysis.get("usage_summary", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one live LLM-enabled submission case and collect artifacts.")
    parser.add_argument("--provider", choices=("modelscope", "deepseek"), default="modelscope")
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--case-id", default="case_llm_financial_review")
    parser.add_argument("--output-dir", default=str(DEST_ROOT))
    parser.add_argument("--run-root", default=str(RUN_ROOT))
    parser.add_argument("--profile", default="financial_report")
    parser.add_argument("--method", default="auto")
    parser.add_argument("--lang", default="ch")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-preview-chars", type=int, default=4000)
    parser.add_argument(
        "--task",
        default=(
            "启用大模型预调度和复核，解析财报 HTML，抽取报告日期、公司名称、合计数字，"
            "检查表格总计并给出可验证证据。"
        ),
    )
    return parser.parse_args()


def build_llm_client(args: argparse.Namespace) -> DeepSeekLLMClient | ModelScopeLLMClient:
    kwargs = {
        "model": args.model,
        "base_url": args.base_url,
        "timeout_seconds": args.timeout,
        "max_preview_chars": args.max_preview_chars,
    }
    if args.provider == "deepseek":
        return DeepSeekLLMClient(**kwargs)
    return ModelScopeLLMClient(**kwargs)


def write_readme(case_dir: Path, args: argparse.Namespace, result: Any) -> None:
    usage = result.llm_analysis.get("usage_summary", {}) if isinstance(result.llm_analysis, dict) else {}
    lines = [
        "# Live LLM Case: Financial Review",
        "",
        f"- Provider: `{args.provider}`",
        f"- Model: `{args.model or 'provider default'}`",
        f"- Input: `{case_dir / ('input' + Path(args.input).suffix.lower())}`",
        f"- Profile: `{result.profile}`",
        f"- Quality: `{result.quality.get('status')}` ({result.quality.get('score')}/100)",
        f"- LLM enabled: `{result.llm_analysis.get('enabled')}`",
        f"- LLM status: `{result.llm_analysis.get('status')}`",
        f"- LLM calls: `{usage.get('tool_call_count', 0)}`",
        f"- LLM total tokens: `{usage.get('total_tokens', 0)}`",
        f"- LLM estimated cost USD: `{usage.get('estimated_cost_usd')}`",
        "",
        "Boundary: API keys are read from environment variables and are not written to artifacts. "
        "Cost is only calculated when provider token usage exists and token-price environment variables are configured.",
        "",
    ]
    (case_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def sanitize_tree(path: Path) -> None:
    for item in path.rglob("*"):
        if not item.is_file() or item.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".html"}:
            continue
        text = item.read_text(encoding="utf-8", errors="replace")
        clean = text.replace(str(PROJECT_ROOT), "<PROJECT_ROOT>")
        clean = clean.replace(str(PROJECT_ROOT).replace("\\", "\\\\"), "<PROJECT_ROOT>")
        item.write_text(clean, encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
