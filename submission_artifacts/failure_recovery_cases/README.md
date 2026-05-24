# Failure And Recovery Cases

These are controlled fault-injection cases. They check failure detection, retry decisions, and audit fields. They are not public-network, GPU, or live OCR benchmarks.

| Case | Trigger | Decision | Selected Attempt | Final Quality | Boundary |
| --- | --- | --- | --- | --- | --- |
| text_cleanup_mojibake | possible_mojibake, document_level_provenance, expected_anomaly_signal_missing | recovered_with_review_notes | text_cleanup | pass_with_warnings (92) | native HTML controlled fixture; validates text cleanup recovery path |
| ocr_retry_success_controlled | short_text | recovered_accept | ocr_retry | pass (100) | controlled fake MinerU runner; validates retry selection logic, not live OCR quality |
| ocr_retry_failure_controlled | short_text | retry_or_manual_review | initial | pass_with_warnings (92) | controlled fake MinerU runner; validates failed-attempt audit trail |
| strict_provenance_failure_controlled | no_page_provenance, weak_clause_structure | strict_page_provenance_failed | initial | needs_review (54) | controlled fake online-API runner; validates strict provenance gate without claiming live API behavior |
| numeric_total_mismatch_html | document_level_provenance, numeric_total_mismatch | manual_numeric_review | initial | pass_with_warnings (92) | native HTML controlled fixture; validates numeric mismatch detection |
