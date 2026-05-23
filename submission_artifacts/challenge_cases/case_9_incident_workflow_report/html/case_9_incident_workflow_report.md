# Incident Workflow Report

Incident ID: OPS-INC-2026-0519

Report Date: 2026-05-23

System: document ingestion and validation pipeline

## 1. Timeline

| Time | Event | Owner | Action |
| --- | --- | --- | --- |
| 09:10 | API parser returned document-level provenance | Agent | trigger fallback policy |
| 09:12 | CLI artifact restored page-level evidence | Parser | select cli_fallback attempt |
| 09:15 | quality gate passed | Validator | archive result and trace |

## 2. Root Cause

Risk: online API Markdown can be structurally useful but insufficient for page-level audit.

Recommendation: route no_page_provenance to CLI fallback when a CLI environment is available.

## 3. Verification Targets

- the separate PDF recovery evidence must show recovery_decision.executed=true

- the separate PDF recovery evidence must show selected_attempt=cli_fallback

- the separate PDF recovery trace must keep both parser attempts