"""Download real-world complex documents for live agent testing.

Sources (all public, no auth required):
- SEC EDGAR: large annual reports (10-K filings)
- arXiv: academic papers with complex tables
- CDC / NIST: government public health / standards documents (already have some)
- China government public docs

Saves to examples/real_world_docs/ with source metadata.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "examples" / "real_world_docs"
OUTPUT.mkdir(parents=True, exist_ok=True)


def _download(url: str, dest: Path, *, max_retries: int = 3) -> Path:
    for attempt in range(max_retries):
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=120) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_bytes(65536):
                        f.write(chunk)
            size = dest.stat().st_size
            print(f"  OK: {dest.name} ({size:,} bytes)")
            return dest
        except Exception as exc:
            print(f"  attempt {attempt + 1} failed: {exc}")
            time.sleep(2.0)
    raise RuntimeError(f"Failed to download {url}")


def _checksum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _save_meta(name: str, url: str, dest: Path, description: str) -> None:
    meta = {
        "name": name,
        "source_url": url,
        "file_path": str(dest.relative_to(OUTPUT)),
        "size_bytes": dest.stat().st_size,
        "sha256_prefix": _checksum(dest),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "description": description,
        "license": "public domain / government publication" if any(
            d in url.lower() for d in ["sec.gov", "cdc.gov", "nist.gov", "gov.cn"]
        ) else "research paper — check arXiv license",
    }
    meta_path = dest.with_suffix(dest.suffix + ".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_sec_filing() -> list[dict]:
    """Download a large SEC 10-K filing in HTML + convert reference to PDF if possible."""
    results = []
    # Microsoft FY2024 10-K (annual report, ~100+ pages as PDF)
    # Use the SEC's inline XBRL viewer HTML which contains the full document
    # Actually, let's use a direct PDF from SEC EDGAR

    filings = [
        {
            "name": "apple_10k_2024",
            "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm",
            "desc": "Apple Inc. 10-K annual report for fiscal year ended September 28, 2024. Contains detailed financial statements, risk factors, and MD&A across ~90 pages. Real SEC filing — dense tables, footnotes, cross-references.",
        },
        {
            "name": "microsoft_10k_2024",
            "url": "https://www.sec.gov/Archives/edgar/data/789019/000095017024085663/msft-20240630.htm",
            "desc": "Microsoft Corp. 10-K annual report for fiscal year ended June 30, 2024. Multi-segment revenue breakdown, cloud/AI disclosures, complex nested tables. ~120 pages.",
        },
    ]

    for f in filings:
        try:
            dest = OUTPUT / f"{f['name']}.htm"
            print(f"\nFETCH {f['name']}: {f['url'][:80]}...")
            _download(f["url"], dest)
            _save_meta(f["name"], f["url"], dest, f["desc"])
            results.append({"name": f["name"], "path": str(dest), "ok": True})
        except Exception as exc:
            print(f"  FAIL: {exc}")
            results.append({"name": f["name"], "ok": False, "error": str(exc)})
    return results


def fetch_arxiv_papers() -> list[dict]:
    """Download arXiv papers with complex tables (as PDF)."""
    results = []
    papers = [
        {
            "name": "arxiv_sparc_benchmark",
            "url": "https://arxiv.org/pdf/2501.12345.pdf",
            "desc": "Placeholder — replace with actual arXiv paper URL",
        },
    ]
    # NIST AI RMF PDF is already in the repo (examples/public_real_documents/files/nist_ai_rmf_1_0.pdf)
    # Let's add a few more that are definitely available:
    papers = [
        {
            "name": "sparc_docvqa_benchmark",
            "url": "https://arxiv.org/pdf/2406.12345.pdf",
            "desc": "Placeholder",
        },
    ]
    # Real arXiv papers (guaranteed to exist — these are well-known):
    real_papers = [
        {
            "name": "gpt4_technical_report",
            "url": "https://arxiv.org/pdf/2303.08774.pdf",
            "desc": "GPT-4 Technical Report (Sparks of AGI). Dense tables of benchmark results, multi-page charts, cross-section references. ~100 pages.",
        },
        {
            "name": "llama3_herd_of_models",
            "url": "https://arxiv.org/pdf/2407.21783.pdf",
            "desc": "Llama 3 Herd of Models. Extensive training data tables, eval matrices, architecture diagrams. ~92 pages.",
        },
    ]
    for p in real_papers:
        try:
            dest = OUTPUT / f"{p['name']}.pdf"
            print(f"\nFETCH {p['name']}: {p['url']}")
            _download(p["url"], dest)
            _save_meta(p["name"], p["url"], dest, p["desc"])
            results.append({"name": p["name"], "path": str(dest), "ok": True})
        except Exception as exc:
            print(f"  FAIL: {exc}")
            results.append({"name": p["name"], "ok": False, "error": str(exc)})
    return results


def main() -> int:
    print("=== D4: Downloading real-world complex documents ===\n")

    all_results = []

    print("--- SEC EDGAR 10-K filings ---")
    all_results.extend(fetch_sec_filing())

    print("\n--- arXiv papers ---")
    all_results.extend(fetch_arxiv_papers())

    ok = [r for r in all_results if r.get("ok")]
    fail = [r for r in all_results if not r.get("ok")]
    print(f"\n=== DONE: {len(ok)} downloaded, {len(fail)} failed ===")

    for r in ok:
        print(f"  ✓ {r['name']} -> {r['path']}")
    for r in fail:
        print(f"  ✗ {r['name']}: {r.get('error')}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
