# MinerU Data Agent Run 18cd14d4f93a

- Task: Parse Microsoft 2024 Annual Report PDF from SEC, extract company identity, annual report signals, financial sections, tables, quality issues, trace, and retrieval chunks.
- Profile: financial_report
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\examples\public_real_documents\files\microsoft_2024_annual_report.pdf`
- Quality: pass_with_warnings (76/100)
- Content blocks: 210
- Pages with provenance: 0
- Provenance level: document
- Sections: 43
- Tables: 3
- Key-values: 0
- Numeric facts: 64
- Dates detected: 0
- Recommendation signals: 4
- Anomaly signals: 6
- Retrieval chunks: 48
- Recovery decision: manual_numeric_review
- Recovery selected attempt: initial
- Recovery attempts: 1
- LLM analysis: disabled

## Plan
1. Inspect input type and task objective
2. Parse document with MinerU or native HTML extractor
3. Normalize content blocks with page-level or document-level provenance
4. Build markdown, section, key-value, table, and numeric views
5. Run quality checks and produce traceable logs
6. Prioritize dense table extraction and numeric consistency checks
7. Flag subtotal/total rows and suspicious numeric cells

## Recommendation Evidence
- This new world is being defined by a rich tapestry of AI agents, which can take action on our behalf, including personal agents across work and life, business process agents, and cross-organizational ones. These agents will be able to work in concert as a new input to help make small businesses more
- AI does not get created without data. At the data layer, we are fundamentally rethinking what it means to be an analytics database or an operational data store in the world of AI. Our Microsoft Intelligent Data Platform provides customers with the broadest capabilities spanning databases, analytics,
- We are continuously applying what we are learning and translating it into security innovation for our customers. A great example is Copilot for Security, which we made generally available this year. It brings together LLMs with domain-specific skills informed by our threat intelligence and 78 trilli
- Finally, we continue our work to create safe experiences online and protect customers from illegal and harmful content and conduct. To bolster our efforts to prevent child sexual exploitation and abuse risks, we have made new commitments to safety by design in our AI services, joined the Tech Coalit

## Recovery Decision
- Decision: manual_numeric_review
- Use local MinerU CLI when page-level provenance is required.
- Route total/subtotal mismatches to numeric review before downstream use.

Attempts:
- initial: pass_with_warnings (76/100), selected

## Issues
- [warning] no_page_provenance: Content blocks were extracted, but no page-level provenance is available.
- [warning] numeric_total_mismatch: A total/subtotal row does not match the sum of comparable numeric rows.
- [info] numeric_total_verified: A total/subtotal row matched the sum of comparable numeric rows.
- [warning] numeric_total_mismatch: A total/subtotal row does not match the sum of comparable numeric rows.

## Markdown Preview

<!-- image-->

Microsoft

Annual Report 2024

Dear shareholders, colleagues, customers, and partners:

Fiscal year 2024 was a pivotal year for Microsoft. We entered our 50th year as a company and the second year of the AI platform shift. With these milestones, I’ve found myself reflecting on how Microsoft has remained a consequential company decade after decade in an industry with no franchise value. And I realize that it’s because—time and time again, when tech paradigms have shifted—we have seized the opportunity to reinvent ourselves to stay relevant to our customers, our partners, and our employees. And that’s what we are doing again today.

Microsoft has been a platform and tools company from the start. We were founded in 1975 with a belief in creating technology that would enable others to create their own. And, nearly 50 years later, this belief remains at the heart of our mission to empower every person and every organization on the planet to achieve more.

This year, we moved from talking about AI to helping our customers translate it into real outcomes—one person, one organization, one institution, and one country at a time. We have made remarkable progress on this front across every industry. For example:

• Coles is generating 1.6 billion daily AI predictions across 850 Australian stores, ensuring every shopper finds what they need.

• Unilever is performing thousands of simulations with AI in the time it would take to run tens of laboratory experiments, as it accelerates its product development.

• Developers at Itaú, Brazil’s largest private bank, are coding more efficiently using our AI pair programmer, GitHub Copilot.

• Khan Academy is making tutoring more accessible for students and helping teachers plan more creative lessons, using our small language model Phi.

• Aquafarmers in Indonesia are improving their yields, thanks to an app built with the Azure OpenAI Service, as well as Azure IoT.

• In Kenya, street vendors now have access to credit for
