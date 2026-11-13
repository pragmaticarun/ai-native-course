"""P4 kit (provided): fictional incidents, a log store that can be flaky, a config repo with
idempotent changes, a health check, a notification outbox and a deterministic triage model.

Everything is about an invented company, Larkspur Pay; the services, hosts and numbers are
made up. The "outside world" (config repo, outbox) lives in SQLite so that tests can check
that side effects happen exactly once even when activities are retried or a worker is killed.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
INCIDENTS: list[dict[str, Any]] = json.loads((HERE / "incidents.json").read_text())
BY_ID = {i["id"]: i for i in INCIDENTS}
CATEGORIES = ("latency", "errors", "availability", "security")


class TransientLogError(RuntimeError):
    """The log backend timed out. Retryable."""


@dataclass
class Classification:
    category: str
    severity: str  # sev1 | sev2 | sev3
    confidence: float


@dataclass
class Proposal:
    cause: str
    change: dict[str, Any] | None  # None = no safe config change; a human must handle it
    rationale: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class ProposeInput:
    incident_id: str
    logs: list[str]


@dataclass
class ChangeInput:
    incident_id: str
    change: dict[str, Any]


@dataclass
class Note:
    key: str
    body: str


@dataclass
class Decision:
    """The human's answer, sent to the workflow as a signal."""

    approver: str
    approve: bool
    change: dict[str, Any] | None = None  # an edited change replaces the proposal's
    reason: str = ""


@dataclass
class TriageResult:
    incident_id: str
    status: str  # resolved | rolled_back | rejected | expired | escalated
    category: str
    severity: str
    cause: str
    change: dict[str, Any] | None = None
    approver: str | None = None
    timeline: dict[str, float] = field(default_factory=dict)  # seconds since start


class World:
    """SQLite-backed outside world: per-service config, change log, outbox, attempts."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        with self._db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS config (service TEXT, key TEXT, value TEXT,"
                " PRIMARY KEY (service, key))"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS changes (key TEXT PRIMARY KEY, service TEXT,"
                " change TEXT, previous TEXT)"
            )
            db.execute("CREATE TABLE IF NOT EXISTS outbox (key TEXT PRIMARY KEY, body TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS attempts (key TEXT, worker TEXT, at REAL)")
            db.execute("CREATE TABLE IF NOT EXISTS log_calls (incident TEXT, at REAL)")

    def _db(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def seed(self, incident: dict[str, Any]) -> None:
        with self._db() as db:
            for k, v in incident["config"].items():
                db.execute(
                    "INSERT OR REPLACE INTO config VALUES (?, ?, ?)",
                    (incident["service"], k, json.dumps(v)),
                )

    def config(self, service: str) -> dict[str, Any]:
        with self._db() as db:
            rows = db.execute("SELECT key, value FROM config WHERE service = ?", (service,))
            return {k: json.loads(v) for k, v in rows}

    def attempt(self, key: str, worker: str) -> None:
        with self._db() as db:
            db.execute("INSERT INTO attempts VALUES (?, ?, ?)", (key, worker, time.time()))

    def attempts(self, prefix: str = "") -> list[str]:
        with self._db() as db:
            rows = db.execute(
                "SELECT key FROM attempts WHERE key LIKE ? ORDER BY at", (prefix + "%",)
            )
            return [r[0] for r in rows]

    def apply_once(
        self, key: str, service: str, change: dict[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        """Apply `change` under idempotency `key`. Returns (previous values, newly_applied).
        A repeated key is a no-op that returns the values recorded the first time."""
        with self._db() as db:
            row = db.execute("SELECT previous FROM changes WHERE key = ?", (key,)).fetchone()
            if row:
                return json.loads(row[0]), False
            current = self.config(service)
            previous = {k: current.get(k) for k in change}
            db.execute(
                "INSERT INTO changes VALUES (?, ?, ?, ?)",
                (key, service, json.dumps(change), json.dumps(previous)),
            )
            for k, v in change.items():
                db.execute(
                    "INSERT OR REPLACE INTO config VALUES (?, ?, ?)", (service, k, json.dumps(v))
                )
            return previous, True

    def changes(self, service: str | None = None) -> list[str]:
        with self._db() as db:
            q = "SELECT key FROM changes" + (" WHERE service = ?" if service else "")
            return [r[0] for r in db.execute(q, (service,) if service else ())]

    def send_once(self, key: str, body: str) -> bool:
        with self._db() as db:
            return (
                db.execute("INSERT OR IGNORE INTO outbox VALUES (?, ?)", (key, body)).rowcount == 1
            )

    def outbox(self, prefix: str = "") -> list[tuple[str, str]]:
        with self._db() as db:
            return list(
                db.execute("SELECT key, body FROM outbox WHERE key LIKE ?", (prefix + "%",))
            )

    def log_call(self, incident: str) -> int:
        with self._db() as db:
            db.execute("INSERT INTO log_calls VALUES (?, ?)", (incident, time.time()))
            return db.execute(
                "SELECT COUNT(*) FROM log_calls WHERE incident = ?", (incident,)
            ).fetchone()[0]


def fetch_logs(world: World, incident_id: str, flaky: bool = False) -> list[str]:
    """The log tool. With `flaky`, the first call per incident times out (TransientLogError)."""
    n = world.log_call(incident_id)
    if flaky and n == 1:
        raise TransientLogError(f"log backend timed out for {incident_id}")
    return list(BY_ID[incident_id]["logs"])


_OPS = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, "==": lambda a, b: a == b}


def healthy(world: World, incident_id: str) -> bool:
    """The service's health check after a change: every `healthy_if` rule holds."""
    inc = BY_ID[incident_id]
    cfg = world.config(inc["service"])
    return bool(inc["healthy_if"]) and all(
        k in cfg and _OPS[op](cfg[k], v) for k, op, v in inc["healthy_if"]
    )


# --------------------------------------------------------------------------- mock model
_CATEGORY_WORDS = {
    "security": ("log in", "login", "certificate", "tls"),
    "availability": ("down", "restarting", "pending", "outage"),
    "latency": ("timing out", "slow", "took", "hours instead"),
    "errors": ("503", "429", "failing", "not being", "rejecting", "not received"),
}


class MockTriageModel:
    """Deterministic stand-in for the model calls. Classification reads only the report
    (what a first responder has); the root cause comes from the logs. `calls` counts uses."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def classify(self, title: str, report: str) -> Classification:
        self.calls.append("classify")
        text = f"{title} {report}".lower()
        for cat in ("security", "availability", "latency", "errors"):
            if any(w in text for w in _CATEGORY_WORDS[cat]):
                sev = (
                    "sev1" if cat in ("security", "availability") or "customers" in text else "sev2"
                )
                return Classification(cat, sev, 0.8)
        return Classification("errors", "sev3", 0.3)

    def propose(self, service: str, config: dict[str, Any], logs: list[str]) -> Proposal:
        self.calls.append("propose")
        text = "\n".join(logs)
        ev = lambda pat: [ln for ln in logs if re.search(pat, ln)]  # noqa: E731
        if m := re.search(r"exceeded timeout_ms=(\d+) \(took (\d+)ms\)", text):
            worst = max(int(x) for x in re.findall(r"took (\d+)ms", text))
            new = int(round(worst * 1.25, -2))
            return Proposal(
                "timeout_too_low",
                {"timeout_ms": max(new, int(m.group(1)) * 2)},
                f"slowest upstream call {worst} ms > timeout",
                ev("timeout_ms"),
            )
        if m := re.search(r"pool \(pool_size=(\d+), waiting=(\d+)\)", text):
            size = int(m.group(1))
            waiting = max(int(x) for x in re.findall(r"waiting=(\d+)", text))
            new = size * 4 if waiting > size else size * 2
            return Proposal(
                "pool_exhausted",
                {"pool_size": new},
                f"{waiting} waiters on a pool of {size}",
                ev("pool_size"),
            )
        if m := re.search(r"flag (\w+)=true rolled out", text):
            if "not found" in text:
                return Proposal(
                    "bad_flag",
                    {m.group(1): False},
                    "errors started with the flag rollout",
                    ev("flag|not found"),
                )
        if m := re.search(r"max_heap_mb=(\d+)", text):
            if "OutOfMemoryError" in text:
                return Proposal(
                    "out_of_memory",
                    {"max_heap_mb": int(m.group(1)) * 2},
                    "heap exhausted, container OOMKilled",
                    ev("heap|OOM"),
                )
        if m := re.search(r"rate_limit_rps=(\d+), partner quota=(\d+)", text):
            quota = int(m.group(2))
            return Proposal(
                "rate_limited",
                {"rate_limit_rps": int(quota * 0.9)},
                f"we send {m.group(1)} rps against a quota of {quota}",
                ev("429"),
            )
        if re.search(r"certificate for \S+ expired", text):
            cur = str(config.get("cert_id", ""))
            year = re.search(r"(\d{4})$", cur)
            renewed = f"{cur[: year.start()]}{int(year.group(1)) + 1}" if year else cur
            return Proposal(
                "cert_expired", {"cert_id": renewed}, "certificate expired", ev("certificate")
            )
        if "connection refused" in text or "outage" in text:
            return Proposal(
                "dependency_down",
                None,
                "a dependency we don't control is down; no config change helps",
                ev("refused|outage"),
            )
        return Proposal("unknown", None, "no known pattern in the logs", [])
