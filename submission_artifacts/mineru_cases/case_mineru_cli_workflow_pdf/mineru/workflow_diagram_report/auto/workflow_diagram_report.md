## Engineering Workflow Inspection Report

Inspection Date: 2026-05-22 System: MinerU Data Agent processing line

## 1. Workflow Diagram

![](images/fa4881571c226c5b8644da690eecad79cf15915ccb02078e137502d7862f2367.jpg)

## 2. Execution Matrix

<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>Input</td><td rowspan=1 colspan=1>Tool</td><td rowspan=1 colspan=1>Expected Output</td><td rowspan=1 colspan=1>Recovery Rule</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>PDF upload</td><td rowspan=1 colspan=1>API layer</td><td rowspan=1 colspan=1>stored file</td><td rowspan=1 colspan=1>reject oversize input</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>document</td><td rowspan=1 colspan=1>MinerU CLI</td><td rowspan=1 colspan=1>markdown and content list</td><td rowspan=1 colspan=1>retry online API</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>content blocks</td><td rowspan=1 colspan=1>validator</td><td rowspan=1 colspan=1>quality report</td><td rowspan=1 colspan=1>mark needs_review</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>markdown</td><td rowspan=1 colspan=1>retrieval exporter</td><td rowspan=1 colspan=1>jsonl chunks</td><td rowspan=1 colspan=1>skip noisy blocks</td></tr></table>

## 3. Findings

Anomaly: a previous API smoke sample was too short and triggered a quality warning.

Recommendation: use richer smoke inputs and keep warnings visible in the result.

## 4. Review Targets

Check that every run has result.json, trace.json, summary.md, and retrieval artifacts.