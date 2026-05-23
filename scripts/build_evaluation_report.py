from __future__ import annotations

import argparse
import json
from pathlib import Path

from mineru_data_agent.evaluation import evaluate_cases, render_markdown_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build labeled evaluation metrics from saved artifacts.")
    parser.add_argument("--labels", default="examples/evaluation/labels.json", help="Evaluation labels JSON.")
    parser.add_argument("--out", default="submission_artifacts/evaluation", help="Output directory.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    output_dir = (project_root / args.out).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = evaluate_cases(project_root / args.labels, project_root=project_root)

    json_path = output_dir / "evaluation_metrics.json"
    md_path = output_dir / "evaluation_metrics.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown_report(report), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
