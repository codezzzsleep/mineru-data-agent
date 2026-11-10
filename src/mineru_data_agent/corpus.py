from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


CATALOG_JSON = "corpus_catalog.json"
CATALOG_JSONL = "corpus_catalog.jsonl"


def build_corpus_catalog(*, root: Path, output_dir: Path | None = None) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    target_dir = Path(output_dir).expanduser().resolve() if output_dir else root
    target_dir.mkdir(parents=True, exist_ok=True)
    entries = [_catalog_entry(skill_path, root=root) for skill_path in sorted(root.rglob("SKILL.md"))]
    entries = [entry for entry in entries if entry]
    payload = {
        "format": "data_agent_corpus_catalog",
        "version": "2026-06-17",
        "root": str(root),
        "total_documents": len(entries),
        "entries": entries,
        "loading_policy": {
            "default_context": ["name", "description", "quality", "package_dir"],
            "policy": "Load this catalog first; then load only the selected document references needed for the task.",
        },
    }
    json_path = target_dir / CATALOG_JSON
    jsonl_path = target_dir / CATALOG_JSONL
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    jsonl_path.write_text(
        "\n".join(json.dumps(entry, ensure_ascii=False) for entry in entries) + ("\n" if entries else ""),
        encoding="utf-8",
    )
    payload["files"] = {"catalog_json": str(json_path), "catalog_jsonl": str(jsonl_path)}
    return payload


def search_corpus_catalog(*, catalog_path: Path, query: str, limit: int = 10) -> list[dict[str, Any]]:
    entries = _load_catalog_entries(catalog_path)
    tokens = _tokens(query)
    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in entries:
        haystack = " ".join(
            str(entry.get(key, ""))
            for key in ["name", "description", "quality", "task", "profile", "package_dir"]
        ).lower()
        score = sum(haystack.count(token) for token in tokens) if tokens else 0
        if score > 0 or not tokens:
            scored.append((score, entry))
    scored.sort(key=lambda item: (-item[0], str(item[1].get("name", ""))))
    return [{**entry, "score": score} for score, entry in scored[: max(1, limit)]]


def load_document_reference(*, package_dir: Path, reference: str = "compressed", max_chars: int = 12000) -> dict[str, Any]:
    package = Path(package_dir).expanduser().resolve()
    allowed = {
        "skill": package / "SKILL.md",
        "overview": package / "references" / "overview.md",
        "compressed": package / "references" / "compressed.md",
        "content": package / "references" / "content.md",
        "structured": package / "references" / "structured.md",
        "tables": package / "references" / "tables.md",
        "evidence": package / "references" / "evidence.md",
        "segments": package / "references" / "segments.md",
        "raw_result": package / "references" / "raw_result.json",
        "retrieval_chunks": package / "references" / "retrieval_chunks.jsonl",
    }
    key = reference if reference in allowed else "overview"
    path = allowed[key]
    if not path.exists() and key == "compressed":
        path = allowed["overview"]
        key = "overview"
    if not path.exists():
        return {"ok": False, "error": "reference_not_found", "reference": reference, "package_dir": str(package)}
    text = path.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > max_chars
    return {
        "ok": True,
        "reference": key,
        "path": str(path),
        "truncated": truncated,
        "chars": len(text),
        "content": text[:max_chars],
    }


def _catalog_entry(skill_path: Path, *, root: Path) -> dict[str, Any]:
    frontmatter = _read_frontmatter(skill_path)
    package_dir = skill_path.parent
    overview = _read_text(package_dir / "references" / "overview.md", limit=8000)
    raw_result = _read_json(package_dir / "references" / "raw_result.json")
    stats = _extract_overview_stats(overview)
    rel_package = str(package_dir.relative_to(root)).replace("\\", "/") if package_dir.is_relative_to(root) else str(package_dir)
    return {
        "name": frontmatter.get("name") or package_dir.name,
        "description": frontmatter.get("description") or "",
        "package_dir": str(package_dir),
        "relative_package_dir": rel_package,
        "task": str(raw_result.get("task", "")) if isinstance(raw_result, dict) else "",
        "profile": str(raw_result.get("profile", "")) if isinstance(raw_result, dict) else "",
        "quality": stats.get("quality", "unknown"),
        "pages": stats.get("pages"),
        "blocks": stats.get("blocks"),
        "tables": stats.get("tables"),
        "retrieval_chunks": stats.get("retrieval_chunks"),
        "references": {
            "skill": str(skill_path),
            "overview": _optional_path(package_dir / "references" / "overview.md"),
            "compressed": _optional_path(package_dir / "references" / "compressed.md"),
            "content": _optional_path(package_dir / "references" / "content.md"),
            "evidence": _optional_path(package_dir / "references" / "evidence.md"),
            "segments": _optional_path(package_dir / "references" / "segments.md"),
        },
    }


def _read_frontmatter(path: Path) -> dict[str, str]:
    text = _read_text(path, limit=4000)
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def _extract_overview_stats(text: str) -> dict[str, Any]:
    stats: dict[str, Any] = {}
    for key, label in [
        ("quality", "Quality"),
        ("blocks", "Blocks"),
        ("pages", "Pages"),
        ("tables", "Tables"),
        ("retrieval_chunks", "Retrieval chunks"),
    ]:
        match = re.search(rf"^- {re.escape(label)}:\s*`?([^`\n]+)`?", text, flags=re.MULTILINE)
        if not match:
            continue
        raw = match.group(1).strip()
        stats[key] = _int_or_raw(raw.split()[0])
    return stats


def _load_catalog_entries(path: Path) -> list[dict[str, Any]]:
    target = Path(path).expanduser().resolve()
    if target.suffix == ".jsonl":
        entries = []
        for line in target.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                item = json.loads(line)
                if isinstance(item, dict):
                    entries.append(item)
        return entries
    data = json.loads(target.read_text(encoding="utf-8", errors="replace"))
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        return [item for item in data["entries"] if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _read_text(path: Path, *, limit: int) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:limit]


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {}


def _optional_path(path: Path) -> str | None:
    return str(path) if path.exists() else None


def _tokens(query: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", query) if token.strip()]


def _int_or_raw(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value
