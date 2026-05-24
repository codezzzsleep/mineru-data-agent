# Cross-run Memory Case

This controlled case runs the same noisy HTML document twice under the same output root.

- First run selected attempt: `text_cleanup`
- First run memory recommendations: `[]`
- Second run memory recommendations: `['text_cleanup']`
- Second runtime memory actions: `['text_cleanup']`

Boundary: local memory is a SQLite statistics table over prior recovery outcomes, not model learning or live LLM autonomy.
