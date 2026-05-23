# MinerU Data Agent Run a9370f880cf5

- Task: Parse the full public NIST AI RMF 1.0 PDF with long-document chunk orchestration; extract publication identity, framework functions, section structure, quality issues, trace, and retrieval chunks. Page range: 1-20.
- Profile: standard_or_contract
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\examples\public_real_documents\files\nist_ai_rmf_1_0.pdf`
- Quality: pass_with_warnings (92/100)
- Content blocks: 120
- Pages with provenance: 0
- Provenance level: document
- Sections: 19
- Tables: 1
- Key-values: 9
- Field evidence records: 9
- Numeric facts: 75
- Dates detected: 0
- Recommendation signals: 9
- Anomaly signals: 50
- Retrieval chunks: 23
- Recovery decision: accept_with_review_notes
- Recovery selected attempt: initial
- Recovery attempts: 1
- LLM analysis: disabled

## Plan
1. Inspect input type and task objective
2. Parse document with MinerU or native HTML extractor
3. Normalize content blocks with page-level or document-level provenance
4. Build markdown, section, key-value, table, and numeric views
5. Run quality checks and produce traceable logs
6. Prioritize section hierarchy and clause-like paragraph extraction
7. Preserve source page or document heading evidence for each clause

## Planning Rationale
- standard/contract keywords or explicit profile require section and clause preservation
- online MinerU Agent API is selected for CPU-friendly PDF parsing and quick reproducibility
- backend=pipeline is used for MinerU parsing when the selected runner calls MinerU
- method=auto balances automatic parsing with OCR fallback when quality gates require it
- lang=en is passed to MinerU or recorded for native extraction audit
- Recovery policy:
  - text_cleanup if mojibake or encoding noise is detected
  - ocr_retry for PDF/image results with blocking extraction or OCR-related quality issues
  - cli_fallback when online API lacks page-level provenance and a local MinerU CLI is available
  - manual_numeric_review when subtotal/total consistency checks fail

## Extracted Fields
- Part 1: Foundational Information 4
- Part 2: Core and Profiles 20
- Appendix A: Descriptions of AI Actor Tasks from Figures 2 and 3 35
- Appendix B: How AI Risks Differ from Traditional Software Risks 38
- Appendix C: AI Risk Management and Human-AI Interaction 40
- Appendix D: Attributes of the AI RMF 42
- https: //www.nist.gov/itl/ai-risk-management-framework.
- ## Part 1: Foundational Information

## Field Evidence
- Part 1: confidence=0.86, location=32, evidence=Executive Summary 1 Part 1: Foundational Information 4 1 Framing Risk 4 1.1 Understanding and Addressing Risks, Impacts, and Harms 4 1.2 Challenges for AI Risk Management 5 1.2.1 Risk Measurement 5 1.2.2 Risk Tolerance 7 1.2.3 Risk Prioritization 7 1.2.4 Organizational Integration and Management of 
- Part 2: confidence=0.86, location=50, evidence=Executive Summary 1 Part 1: Foundational Information 4 1 Framing Risk 4 1.1 Understanding and Addressing Risks, Impacts, and Harms 4 1.2 Challenges for AI Risk Management 5 1.2.1 Risk Measurement 5 1.2.2 Risk Tolerance 7 1.2.3 Risk Prioritization 7 1.2.4 Organizational Integration and Management of 
- Appendix A: confidence=0.86, location=57, evidence=Executive Summary 1 Part 1: Foundational Information 4 1 Framing Risk 4 1.1 Understanding and Addressing Risks, Impacts, and Harms 4 1.2 Challenges for AI Risk Management 5 1.2.1 Risk Measurement 5 1.2.2 Risk Tolerance 7 1.2.3 Risk Prioritization 7 1.2.4 Organizational Integration and Management of 
- Appendix B: confidence=0.86, location=58, evidence=Executive Summary 1 Part 1: Foundational Information 4 1 Framing Risk 4 1.1 Understanding and Addressing Risks, Impacts, and Harms 4 1.2 Challenges for AI Risk Management 5 1.2.1 Risk Measurement 5 1.2.2 Risk Tolerance 7 1.2.3 Risk Prioritization 7 1.2.4 Organizational Integration and Management of 
- Appendix C: confidence=0.86, location=59, evidence=Executive Summary 1 Part 1: Foundational Information 4 1 Framing Risk 4 1.1 Understanding and Addressing Risks, Impacts, and Harms 4 1.2 Challenges for AI Risk Management 5 1.2.1 Risk Measurement 5 1.2.2 Risk Tolerance 7 1.2.3 Risk Prioritization 7 1.2.4 Organizational Integration and Management of 

## Recommendation Evidence
- Certain commercial entities, equipment, or materials may be identified in this document in order to describe an experimental procedure or concept adequately. Such identification is not intended to imply recommendation or endorsement by the National Institute of Standards and Technology, nor is it in
- Appendix C: AI Risk Management and Human-AI Interaction 40
- The AI RMF refers to an AI system as an engineered or machine-based system that can, for a given set of objectives, generate outputs such as predictions, recommendations, or decisions influencing real or virtual environments. AI systems are designed to operate with varying levels of autonomy (Adapte
- While there are myriad standards and best practices to help organizations mitigate the risks of traditional software or information-based systems, the risks posed by AI systems are in many ways unique (See Appendix B). AI systems, for example, may be trained on data that can change over time, someti
- Development of the AI RMF by NIST in collaboration with the private and public sectors is directed and consistent with its broader AI efforts called for by the National AI Initiative Act of 2020, the National Security Commission on Artificial Intelligence recommendations, and the Plan for Federal En

## Recovery Decision
- Decision: accept_with_review_notes
- Use local MinerU CLI when page-level provenance is required.

Attempts:
- initial: pass_with_warnings (92/100), selected

## Issues
- [warning] no_page_provenance: Content blocks were extracted, but no page-level provenance is available.

## Markdown Preview

<!-- image-->

Artificial Intelligence Risk Management Framework (AI RMF 1.0)

NST NNATINIOL GEA GSTUIE OF STANDARDS AND TECHNOLOGYU.S. DEPARTMENT OF COMMERCE

NIST AI 100-1

# Artificial Intelligence Risk Management Framework (AI RMF 1.0)

This publication is available free of charge from: https://doi.org/10.6028/NIST.AI.100-1

January 2023

<!-- image-->

U.S. Department of Commerce Gina M. Raimondo, Secretary

Certain commercial entities, equipment, or materials may be identified in this document in order to describe an experimental procedure or concept adequately. Such identification is not intended to imply recommendation or endorsement by the National Institute of Standards and Technology, nor is it intended to imply that the entities, materials, or equipment are necessarily the best available for the purpose.

This publication is available free of charge from: https://doi.org/10.6028/NIST.AI.100-1

## Update Schedule and Versions

The Artificial Intelligence Risk Management Framework (AI RMF) is intended to be a living document.

NIST will review the content and usefulness of the Framework regularly to determine if an update is appropriate; a review with formal input from the AI community is expected to take place no later than 2028. The Framework will employ a two-number versioning system to track and identify major and minor changes. The first number will represent the generation of the AI RMF and its companion documents (e.g., 1.0) and will change only with major revisions. Minor revisions will be tracked using “.n” after the generation number (e.g., 1.1). All changes will be tracked using a Version Control Table which identifies the history, including version number, date of change, and description of change. NIST plans to update the AI RMF Playbook frequently. Comments on the AI RMF Playbook may be sent via email to AIframework@nist.gov at any time and will be reviewed and integrated on a semi-annual basis.

## Table of Contents

Executive Summary 1   
P
