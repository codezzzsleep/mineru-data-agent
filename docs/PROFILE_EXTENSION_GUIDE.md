# Profile Extension Guide

This project treats a document profile as a deterministic routing and validation policy. A new profile does not require changing the API contract, but it should add its own schema, checks, fixtures, and labels.

## Add A Profile

1. Add the profile id to `PROFILE_CHOICES` in `src/mineru_data_agent/planner.py`.
2. Extend `infer_profile()` with conservative task/file keywords.
3. Add default fields in `_default_schema()`.
4. Add task-specific processors in `_post_processors()` and validation focus in `_verification_focus()`.
5. Add quality thresholds and recovery preferences in `_quality_thresholds()` and `_recovery_strategy()`.
6. Add validator logic only when the profile has a measurable failure mode, such as numeric total mismatch, missing provenance, or short OCR text.
7. Add one fixture under `examples/` and one saved artifact under `submission_artifacts/`.
8. Add labels to `examples/evaluation/labels.json` when the profile claims measurable extraction quality.
9. Add tests for profile inference, planning fields, quality issue codes, and any new post-processor.

## Minimal Acceptance Bar

| Requirement | Evidence |
| --- | --- |
| Profile is selected for the right task | planner unit test |
| Target schema is explicit | `execution_control.adaptive_decision.target_schema` |
| Quality risks are visible | `quality.issues[*].code` |
| Recovery behavior is auditable | `recovery_decision.attempts` |
| Retrieval export is still valid | `submission_artifacts/retrieval_validation/` |
| Labels are not self-confirming | `submission_artifacts/evaluation/` with human-readable expected evidence |

## Current Limits

- Profiles are deterministic policies with optional LLM merge points, not learned adapters.
- Adding a profile does not automatically improve OCR, visual graph parsing, or table-cell accuracy.
- Claims about a new industry vertical should be backed by labels and at least one failure case, not only a happy-path fixture.
