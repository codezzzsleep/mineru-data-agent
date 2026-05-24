# Quick Decision Guide

## Which Runner Should I Use?

| Situation | Suggested setting |
| --- | --- |
| CPU-only review or quick API smoke | `--runner agent-api` |
| Need page-level PDF evidence and MinerU is installed | `--runner cli` |
| HTML, DOCX, or PPTX input | native extractor branch; no MinerU runner is called |
| Audit task requires page provenance | add `--strict-page-provenance` |
| Online API lacks page provenance but local CLI is available | set `--fallback-mineru-executable` or `MINERU_EXECUTABLE` |

## Speed Or Auditability?

| Goal | Suggested path | Tradeoff |
| --- | --- | --- |
| Fast smoke test | online Agent API, `method=auto` | may return document-level provenance |
| Stronger evidence | local MinerU CLI, `method=auto` | needs local MinerU/GPU environment |
| Sparse scanned PDF | local CLI or API with OCR retry enabled | slower but records retry attempts |
| Strict review | `--strict-page-provenance` | returns `needs_review` if page evidence is missing |

## Common Problems

| Symptom | What to check |
| --- | --- |
| `no_page_provenance` | Online API output is document-level. Use local CLI fallback or strict mode for audit tasks. |
| `strict_page_provenance_failed` | The result is partial for audit use. Rerun with a parser path that emits page evidence. |
| `short_text` | Source may need OCR. Check `recovery_decision.attempts` for `ocr_retry`. |
| `numeric_total_mismatch` | Do not auto-accept financial totals. Route to numeric review and inspect table evidence. |
| LLM disabled | Set `--llm deepseek` or `--llm modelscope` and provide provider credentials through environment variables. |

## Minimal Python Integration

```python
from mineru_data_agent.agent import MinerUDataAgent

agent = MinerUDataAgent()
result = agent.run(
    "report.html",
    "runs",
    task="抽取关键字段、质量问题和检索 chunks",
    profile="auto",
)

print(result.quality["status"])
print(result.extracted["key_value_map"])
```
