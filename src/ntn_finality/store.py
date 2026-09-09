from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .errors import Code, FinalityError
from .models import ProtectedValidationEvidence, SatelliteFinalityAuthority, iso_z


class SQLiteFinalityStore:
    """Reference durability and single-node consume semantics."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, isolation_level=None, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON")
        if self._path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS evidence (
          evidence_id TEXT PRIMARY KEY,
          candidate_act_id TEXT NOT NULL,
          candidate_act_digest TEXT NOT NULL,
          grant_digest TEXT NOT NULL,
          payload TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS authorities (
          authority_id TEXT PRIMARY KEY,
          candidate_act_id TEXT NOT NULL,
          evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id),
          candidate_act_digest TEXT NOT NULL,
          grant_digest TEXT NOT NULL,
          nonce TEXT NOT NULL UNIQUE,
          sink_id TEXT NOT NULL,
          state TEXT NOT NULL CHECK(state IN ('UNUSED','CONSUMED_PENDING','EFFECTED','FAILED_DEFINITE')),
          effect_id TEXT,
          payload TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_effected_grant
          ON authorities(grant_digest)
          WHERE state IN ('CONSUMED_PENDING','EFFECTED');
        """)

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
            else:
                self._conn.execute("COMMIT")

    def commit_evidence(self, evidence: ProtectedValidationEvidence) -> None:
        with self._tx() as db:
            db.execute("INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?)", (
                evidence.evidence_id, evidence.candidate_act_id,
                evidence.candidate_act_digest, evidence.grant_digest,
                json.dumps(evidence.to_dict(), sort_keys=True), iso_z(evidence.issued_at),
            ))

    def evidence(self, evidence_id: str) -> dict | None:
        row = self._conn.execute("SELECT payload FROM evidence WHERE evidence_id=?", (evidence_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def register(self, authority: SatelliteFinalityAuthority) -> None:
        with self._tx() as db:
            db.execute("INSERT INTO authorities VALUES (?, ?, ?, ?, ?, ?, ?, 'UNUSED', NULL, ?, ?)", (
                authority.authority_id, authority.candidate_act_id, authority.evidence_id,
                authority.binding["candidate_act_digest"], authority.binding["grant_digest"]["value"],
                authority.binding["nonce"], authority.binding["finality_sink_id"],
                json.dumps(authority.to_dict(), sort_keys=True), iso_z(datetime.now(timezone.utc)),
            ))

    def reserve(self, authority_id: str, grant_digest: str, sink_id: str) -> None:
        with self._tx() as db:
            row = db.execute("SELECT state, grant_digest, sink_id FROM authorities WHERE authority_id=?", (authority_id,)).fetchone()
            if row is None:
                raise FinalityError(Code.NO_FINALITY_AUTHORITY, "authority is not registered")
            if row["state"] != "UNUSED":
                raise FinalityError(Code.AUTHORITY_ALREADY_USED, f"authority state is {row['state']}")
            if row["grant_digest"] != grant_digest:
                raise FinalityError(Code.GRANT_SUBSTITUTION, "registered grant digest differs")
            if row["sink_id"] != sink_id:
                raise FinalityError(Code.SINK_MISMATCH, "registered sink differs")
            try:
                changed = db.execute(
                    "UPDATE authorities SET state='CONSUMED_PENDING', updated_at=? WHERE authority_id=? AND state='UNUSED'",
                    (iso_z(datetime.now(timezone.utc)), authority_id),
                ).rowcount
            except sqlite3.IntegrityError as exc:
                raise FinalityError(Code.REPLAY_DETECTED, "grant digest already consumed") from exc
            if changed != 1:
                raise FinalityError(Code.AUTHORITY_ALREADY_USED, "concurrent consume lost")

    def complete(self, authority_id: str, effect_id: str) -> None:
        with self._tx() as db:
            changed = db.execute(
                "UPDATE authorities SET state='EFFECTED', effect_id=?, updated_at=? "
                "WHERE authority_id=? AND state='CONSUMED_PENDING'",
                (effect_id, iso_z(datetime.now(timezone.utc)), authority_id),
            ).rowcount
            if changed != 1:
                raise FinalityError(Code.FAIL_CLOSED, "authority was not reserved")

    def fail_definite(self, authority_id: str) -> None:
        with self._tx() as db:
            db.execute(
                "UPDATE authorities SET state='FAILED_DEFINITE', updated_at=? "
                "WHERE authority_id=? AND state='CONSUMED_PENDING'",
                (iso_z(datetime.now(timezone.utc)), authority_id),
            )

    def state(self, authority_id: str) -> str | None:
        row = self._conn.execute("SELECT state FROM authorities WHERE authority_id=?", (authority_id,)).fetchone()
        return row[0] if row else None

    def close(self) -> None:
        self._conn.close()

