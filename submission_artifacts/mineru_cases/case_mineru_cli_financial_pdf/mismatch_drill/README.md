# Financial Mismatch Drill

This directory is a validator drill, not a new MinerU parser run.

Purpose: prove the total-row rule can fail when a comparable numeric value is inconsistent. The table below intentionally changes the total row to `150` while the comparable source rows sum to `160`. The resulting `mismatch_quality.json` contains `numeric_total_mismatch`.

Boundary: this drill validates the post-processing rule only. It does not claim PDF OCR accuracy or accounting correctness.
