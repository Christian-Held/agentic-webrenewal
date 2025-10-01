"""Persistent storage helpers for the post-edit pipeline."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .postedit.models import ChangeSet, SiteState


def _iso_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


@dataclass(slots=True)
class EditRecord:
    """Representation of an edit stored in the database."""

    id: str
    scope: str
    prompt: str | None
    change_set_hash: str
    created_at: str


class StateStore:
    """Simple SQLite backed storage for persistent state."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    kind TEXT,
                    path TEXT,
                    hash TEXT,
                    created_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS site_state (
                    id TEXT PRIMARY KEY,
                    key TEXT UNIQUE,
                    value_json TEXT,
                    updated_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS edits (
                    id TEXT PRIMARY KEY,
                    scope TEXT,
                    prompt TEXT,
                    llm_meta_json TEXT,
                    diff_stats_json TEXT,
                    created_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS previews (
                    id TEXT PRIMARY KEY,
                    old_dir TEXT,
                    new_dir TEXT,
                    index_path TEXT,
                    created_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS trace (
                    id TEXT PRIMARY KEY,
                    provider TEXT,
                    model TEXT,
                    request_trunc TEXT,
                    response_trunc TEXT,
                    duration_ms INTEGER,
                    created_at TEXT,
                    tokens_json TEXT
                )
                """
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Site state
    # ------------------------------------------------------------------
    def load_site_state(self, *, key: str = "current") -> SiteState:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT value_json FROM site_state WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
        payload: Dict[str, Any] | None = None
        if row and row[0]:
            payload = json.loads(row[0])
        return SiteState.from_dict(payload)

    def save_site_state(self, state: SiteState, *, key: str = "current") -> None:
        payload = json.dumps(state.to_dict(), ensure_ascii=False)
        now = _iso_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO site_state(id, key, value_json, updated_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json=excluded.value_json,
                    updated_at=excluded.updated_at
                """,
                (uuid.uuid4().hex, key, payload, now),
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Artifacts
    # ------------------------------------------------------------------
    def record_artifact(self, kind: str, path: Path, *, file_hash: str | None = None) -> str:
        artifact_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO artifacts(id, kind, path, hash, created_at) VALUES(?,?,?,?,?)",
                (artifact_id, kind, str(path), file_hash, _iso_now()),
            )
            conn.commit()
        return artifact_id

    # ------------------------------------------------------------------
    # Edits
    # ------------------------------------------------------------------
    def record_edit(
        self,
        *,
        scope: str,
        prompt: str | None,
        change_set: ChangeSet,
        diff_stats: Dict[str, Any],
        llm_meta: Dict[str, Any] | None = None,
    ) -> str:
        entry_id = uuid.uuid4().hex
        diff_payload = dict(diff_stats)
        diff_payload.setdefault("change_set_hash", change_set.hash())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO edits(id, scope, prompt, llm_meta_json, diff_stats_json, created_at)"
                " VALUES(?,?,?,?,?,?)",
                (
                    entry_id,
                    scope,
                    prompt,
                    json.dumps(llm_meta or {}, ensure_ascii=False),
                    json.dumps(diff_payload, ensure_ascii=False),
                    _iso_now(),
                ),
            )
            conn.commit()
        return entry_id

    def list_edits(self) -> list[EditRecord]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id, scope, prompt, diff_stats_json, created_at FROM edits ORDER BY created_at DESC"
            )
            rows = cursor.fetchall()
        edits: list[EditRecord] = []
        for row in rows:
            diff_stats = json.loads(row["diff_stats_json"]) if row["diff_stats_json"] else {}
            edits.append(
                EditRecord(
                    id=row["id"],
                    scope=row["scope"],
                    prompt=row["prompt"],
                    change_set_hash=str(diff_stats.get("change_set_hash", "")),
                    created_at=row["created_at"],
                )
            )
        return edits

    def has_change_set(self, change_hash: str) -> bool:
        if not change_hash:
            return False
        with self._connect() as conn:
            cursor = conn.execute("SELECT diff_stats_json FROM edits")
            rows = cursor.fetchall()
        for row in rows:
            if not row[0]:
                continue
            data = json.loads(row[0])
            if data.get("change_set_hash") == change_hash:
                return True
        return False

    # ------------------------------------------------------------------
    # Previews
    # ------------------------------------------------------------------
    def record_preview(self, *, old_dir: Path | None, new_dir: Path, index_path: Path) -> str:
        preview_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO previews(id, old_dir, new_dir, index_path, created_at) VALUES(?,?,?,?,?)",
                (
                    preview_id,
                    str(old_dir) if old_dir else None,
                    str(new_dir),
                    str(index_path),
                    _iso_now(),
                ),
            )
            conn.commit()
        return preview_id

    def latest_preview(self) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id, old_dir, new_dir, index_path, created_at FROM previews ORDER BY created_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "old_dir": row["old_dir"],
            "new_dir": row["new_dir"],
            "index_path": row["index_path"],
            "created_at": row["created_at"],
        }

    # ------------------------------------------------------------------
    # Trace logging
    # ------------------------------------------------------------------
    def record_trace(
        self,
        *,
        provider: str,
        model: str,
        request_trunc: str,
        response_trunc: str,
        duration_ms: int,
        tokens: Dict[str, Any] | None = None,
    ) -> str:
        trace_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO trace(id, provider, model, request_trunc, response_trunc, duration_ms, created_at, tokens_json)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (
                    trace_id,
                    provider,
                    model,
                    request_trunc,
                    response_trunc,
                    duration_ms,
                    _iso_now(),
                    json.dumps(tokens or {}, ensure_ascii=False),
                ),
            )
            conn.commit()
        return trace_id


def default_state_store(base_dir: Path) -> StateStore:
    """Return a state store located under ``base_dir``."""

    db_path = base_dir / "state.db"
    return StateStore(db_path)


__all__ = ["default_state_store", "EditRecord", "StateStore"]

