from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AgentMemoryStore:
    """Small per-output-root memory for recovery outcome statistics."""

    def __init__(self, output_root: Path) -> None:
        self.enabled = os.getenv("MINERU_DATA_AGENT_MEMORY", "1").strip().lower() not in {"0", "false", "off"}
        self.path = output_root / ".mineru_data_agent" / "memory.sqlite"
        if self.enabled:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()

    def summarize(self, *, profile: str, issue_codes: list[str]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "enabled": self.enabled,
            "path": str(self.path) if self.enabled else None,
            "profile": profile,
            "issue_codes": issue_codes,
            "stats": [],
            "recommended_actions": [],
            "boundary": "Local SQLite memory records recovery outcomes under the selected output root; it is simple statistics, not model fine-tuning.",
        }
        if not self.enabled or not self.path.exists():
            return payload
        issue_set = set(issue_codes)
        rows = self._fetch_rows(profile)
        aggregate: dict[str, dict[str, Any]] = {}
        for row in rows:
            row_issues = set(json.loads(row["issue_codes_json"] or "[]"))
            if issue_set and not (issue_set & row_issues):
                continue
            action = str(row["selected_attempt"] or "initial")
            stats = aggregate.setdefault(action, {"action": action, "attempts": 0, "successes": 0, "score_sum": 0})
            stats["attempts"] += 1
            stats["score_sum"] += int(row["quality_score"] or 0)
            if row["quality_status"] == "pass" and action != "initial":
                stats["successes"] += 1
        rendered = []
        for stats in aggregate.values():
            attempts = int(stats["attempts"])
            successes = int(stats["successes"])
            rendered.append(
                {
                    "action": stats["action"],
                    "attempts": attempts,
                    "successes": successes,
                    "success_rate": round(successes / attempts, 4) if attempts else 0.0,
                    "avg_quality_score": round(float(stats["score_sum"]) / attempts, 2) if attempts else 0.0,
                }
            )
        rendered.sort(key=lambda item: (item["success_rate"], item["successes"], item["avg_quality_score"]), reverse=True)
        payload["stats"] = rendered
        payload["recommended_actions"] = [
            item["action"] for item in rendered if item["action"] != "initial" and item["successes"] > 0
        ][:3]
        return payload

    def record(
        self,
        *,
        run_id: str,
        profile: str,
        initial_issue_codes: list[str],
        selected_attempt: str,
        decision: str,
        quality_status: str,
        quality_score: int,
    ) -> None:
        if not self.enabled:
            return
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO recovery_outcomes
                (run_id, created_at, profile, issue_codes_json, selected_attempt, decision, quality_status, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    profile,
                    json.dumps(initial_issue_codes, ensure_ascii=False),
                    selected_attempt,
                    decision,
                    quality_status,
                    int(quality_score or 0),
                ),
            )

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    issue_codes_json TEXT NOT NULL,
                    selected_attempt TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    quality_status TEXT NOT NULL,
                    quality_score INTEGER NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_recovery_profile ON recovery_outcomes(profile)")

    def _fetch_rows(self, profile: str) -> list[sqlite3.Row]:
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            return list(
                conn.execute(
                    """
                    SELECT issue_codes_json, selected_attempt, quality_status, quality_score
                    FROM recovery_outcomes
                    WHERE profile = ?
                    ORDER BY id DESC
                    LIMIT 200
                    """,
                    (profile,),
                )
            )
