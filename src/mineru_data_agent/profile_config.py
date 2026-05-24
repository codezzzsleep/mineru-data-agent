from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from math import sqrt
from pathlib import Path
from typing import Any


DEFAULT_PROFILE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "financial_report": {
        "description": "Financial reports, revenue, profit, cash flow, assets, liabilities, dense numeric tables, subtotals, totals, variance and growth analysis.",
        "keywords": ["财报", "报表", "资产", "负债", "利润", "收入", "现金流", "合计", "finance", "financial", "revenue", "profit", "cash", "table"],
    },
    "standard_or_contract": {
        "description": "Contracts, standards, clauses, obligations, parties, effective dates, compliance requirements, penalties, legal or policy terms.",
        "keywords": ["规范", "标准", "条款", "合同", "甲方", "乙方", "处罚", "合规", "standard", "clause", "contract", "policy", "penalty"],
    },
    "workflow_or_diagram": {
        "description": "Workflow reports, process diagrams, engineering drawings, nodes, steps, decisions, incident flow, tools, inputs and outputs.",
        "keywords": ["流程", "工艺", "工程图", "图纸", "节点", "步骤", "flow", "workflow", "diagram", "process"],
    },
    "low_quality_ocr": {
        "description": "Scanned, photographed, blurry, noisy, low quality OCR documents, sparse text, mojibake and image-based pages.",
        "keywords": ["扫描", "拍照", "模糊", "低质量", "乱码", "ocr", "scan", "scanned", "blurry", "noisy"],
    },
    "general_document": {
        "description": "General documents that do not require a specialized financial, contract, workflow or OCR path.",
        "keywords": ["文档", "报告", "说明", "document", "report", "general"],
    },
}


@dataclass(frozen=True)
class ProfileMatch:
    profile: str
    score: float
    keyword_hits: list[str]
    semantic_score: float
    source: str

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "score": round(self.score, 4),
            "keyword_hits": self.keyword_hits,
            "semantic_score": round(self.semantic_score, 4),
            "source": self.source,
        }


def profile_choices() -> set[str]:
    return set(load_profile_definitions())


def infer_profile_with_evidence(task: str, filename: str) -> dict[str, Any]:
    query = f"{task} {filename}".strip()
    definitions = load_profile_definitions()
    matches = [_score_profile(profile, definition, query) for profile, definition in definitions.items()]
    matches.sort(key=lambda item: (item.score, item.profile != "general_document"), reverse=True)
    best = matches[0] if matches else ProfileMatch("general_document", 0.0, [], 0.0, "default")
    if best.score <= 0:
        best = ProfileMatch("general_document", 0.0, [], 0.0, "default")
    return {
        "selected_profile": best.profile,
        "source": best.source,
        "method": "config_keyword_and_lightweight_semantic_vector",
        "config_path": _profile_config_path(),
        "matches": [item.to_jsonable() for item in matches[:5]],
        "boundary": "Profile inference uses configurable keywords plus lightweight token/character vector similarity; it is deterministic and not a learned embedding model.",
    }


def infer_profile_from_config(task: str, filename: str) -> str:
    return str(infer_profile_with_evidence(task, filename)["selected_profile"])


@lru_cache(maxsize=4)
def load_profile_definitions(config_path: str | None = None) -> dict[str, dict[str, Any]]:
    path = config_path or _profile_config_path()
    definitions = {key: dict(value) for key, value in DEFAULT_PROFILE_DEFINITIONS.items()}
    if not path:
        return definitions
    config_file = Path(path).expanduser()
    if not config_file.exists():
        return definitions
    data = json.loads(config_file.read_text(encoding="utf-8"))
    raw_profiles = data.get("profiles", data) if isinstance(data, dict) else {}
    if not isinstance(raw_profiles, dict):
        return definitions
    for profile, payload in raw_profiles.items():
        if not isinstance(payload, dict):
            continue
        name = str(profile).strip()
        if not name:
            continue
        definitions[name] = {
            "description": str(payload.get("description") or definitions.get(name, {}).get("description") or ""),
            "keywords": _string_list(payload.get("keywords") or definitions.get(name, {}).get("keywords") or []),
        }
    return definitions


def _profile_config_path() -> str:
    return os.getenv("MINERU_DATA_AGENT_PROFILE_CONFIG", "").strip()


def _score_profile(profile: str, definition: dict[str, Any], query: str) -> ProfileMatch:
    lowered = query.lower()
    keywords = _string_list(definition.get("keywords"))
    hits = [keyword for keyword in keywords if keyword.lower() in lowered]
    keyword_score = len(hits) / max(len(keywords), 1)
    semantic_score = _cosine(_vectorize(query), _vectorize(f"{profile} {definition.get('description', '')} {' '.join(keywords)}"))
    score = (0.68 * keyword_score) + (0.32 * semantic_score)
    source = "profile_config" if _profile_config_path() else "built_in_profile_config"
    return ProfileMatch(profile=profile, score=score, keyword_hits=hits[:12], semantic_score=semantic_score, source=source)


def _vectorize(text: str) -> dict[str, float]:
    tokens = _tokens(text)
    vector: dict[str, float] = {}
    for token in tokens:
        vector[token] = vector.get(token, 0.0) + 1.0
    return vector


def _tokens(text: str) -> list[str]:
    lowered = text.lower()
    words = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", lowered)
    cjk_text = "".join(re.findall(r"[\u4e00-\u9fff]", lowered))
    cjk_bigrams = [cjk_text[index : index + 2] for index in range(max(0, len(cjk_text) - 1))]
    return words + cjk_bigrams


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0.0) for key, value in left.items())
    left_norm = sqrt(sum(value * value for value in left.values()))
    right_norm = sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
