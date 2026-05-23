# MinerU Data Agent Run d6f8646990e9

- Task: Parse the public CDC VIS instruction PDF, extract instruction title, responsible agency, legal-use statements, quality issues, trace, and retrieval chunks.
- Profile: standard_or_contract
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\examples\public_real_documents\files\cdc_vis_instructions.pdf`
- Quality: pass_with_warnings (84/100)
- Content blocks: 28
- Pages with provenance: 0
- Provenance level: document
- Sections: 7
- Tables: 0
- Key-values: 17
- Numeric facts: 9
- Dates detected: 0
- Recommendation signals: 0
- Anomaly signals: 0
- Retrieval chunks: 5
- Recovery decision: accept_with_review_notes
- Recovery selected attempt: initial
- Recovery attempts: 2
- LLM analysis: disabled

## Plan
1. Inspect input type and task objective
2. Parse document with MinerU or native HTML extractor
3. Normalize content blocks with page-level or document-level provenance
4. Build markdown, section, key-value, table, and numeric views
5. Run quality checks and produce traceable logs
6. Prioritize section hierarchy and clause-like paragraph extraction
7. Preserve source page or document heading evidence for each clause

## Extracted Fields
- DTaP (Diphtheria, Tetanus, Pertussis): 8/6/21
- Hepatitis A: 1/31/25
- Hepatitis B†: 1/31/25
- HPV (Human Papillomavirus): 8/6/21
- Influenza (inactivated): 1/31/25
- Influenza (live): 1/31/25
- MMR: 1/31/25
- MMRV: 1/31/25

## Recovery Decision
- Decision: accept_with_review_notes
- Executed 1 automatic recovery attempt(s); selected `initial`.
- Use local MinerU CLI when page-level provenance is required.

Attempts:
- initial: pass_with_warnings (84/100), selected
- ocr_retry: pass_with_warnings (84/100), not selected

## Issues
- [warning] no_page_provenance: Content blocks were extracted, but no page-level provenance is available.
- [warning] expected_anomaly_signal_missing: Task asks for anomalies/risks, but no anomaly-like evidence was extracted.

## Markdown Preview

# Vaccine Information Statements

## Required Use

## 1. Provide a Vaccine Information Statement (VIS) when a vaccination is given.

As required under the National Childhood Vaccine Injury Act (42 U.S.C. §300aa-26), all health care providers in the United States who administer, to any child or adult, any of the following vaccines — diphtheria, tetanus, pertussis, measles, mumps, rubella, polio, hepatitis A, hepatitis B, Haemophilus influenzae type b (Hib), influenza, pneumococcal conjugate, meningococcal, rotavirus, human papillomavirus (HPV), or varicella (chickenpox) — shall, prior to administration of each dose of the vaccine, provide a copy to keep of the relevant current edition vaccine information materials that have been produced by the Centers for Disease Control and Prevention (CDC):

 to the parent or legal representative1 of any child to whom the provider intends to administer such vaccine, OR

 to any adult2 to whom the provider intends to administer such vaccine.

If there is not a single VIS for a combination vaccine, use the VISs for all component vaccines.

VISs should be supplemented with visual presentations or oral explanations as appropriate.

## 2. Record information for each VIS provided.

Health care providers shall make a notation in each patient’s permanent medical record at the time vaccine information materials are provided, indicating:

- (1) the edition date of the Vaccine Information Statement distributed, and

- (2) the date the VIS was provided.

This recordkeeping requirement supplements the requirement of 42 U.S.C. §300aa-25 that all health care providers administering these vaccines must record in the patient’s permanent medical record (or in a permanent office log):

- (3) the name, address and title of the individual who administers the vaccine,

- (4) the date of administration, and

- (5) the vaccine manufacturer and lot number of the vaccine used.

1 “Legal representative” is defined as a parent or other individual who is qu
