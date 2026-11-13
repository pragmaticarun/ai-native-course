"""M13 L13.4 / Ex3: our own hybrid router (local LiteRT-LM vs a cloud model), PII first.

Order of checks: privacy class and detected PII -> connectivity -> on-device availability ->
context fit -> task difficulty -> battery. PII never leaves the device: if the local model
can't take it, we *refuse* rather than fall back to the cloud.

`firebase_mode_route` shows how Firebase AI Logic's documented modes (PREFER_ON_DEVICE,
ONLY_ON_DEVICE, PREFER_IN_CLOUD, ONLY_IN_CLOUD) would resolve; on a Galaxy A73 the on-device
half (Gemini Nano) is unavailable, so PREFER_ON_DEVICE resolves to the cloud. That outcome is
*inferred from the device lists, not observed (untested)*.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

PII = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),
    "phone": re.compile(r"(?<!\d)(?:\+?\d[\d -]{8,}\d)(?!\d)"),
    "card": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "id_number": re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"),  # 12-digit grouped IDs
}


class Privacy(Enum):
    PUBLIC = 1
    PERSONAL = 2
    SENSITIVE = 3  # health, finance, credentials: on-device only


class Route(Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    REFUSE = "refuse"


@dataclass(frozen=True)
class Request:
    prompt: str
    privacy: Privacy = Privacy.PUBLIC
    hard: bool = False  # e.g. long summary, multi-step reasoning
    est_tokens: int = 200


@dataclass(frozen=True)
class DeviceState:
    online: bool = True
    local_available: bool = True
    local_ctx_tokens: int = 4096
    battery_pct: int = 80
    charging: bool = False


def detect_pii(text: str) -> list[str]:
    return [k for k, rx in PII.items() if rx.search(text)]


def route(req: Request, dev: DeviceState) -> tuple[Route, str]:
    pii = detect_pii(req.prompt)
    must_stay = req.privacy is Privacy.SENSITIVE or bool(pii)
    fits = req.est_tokens <= dev.local_ctx_tokens
    if must_stay:
        if dev.local_available and fits:
            return Route.LOCAL, f"must stay on device ({', '.join(pii) or req.privacy.name})"
        return (
            Route.REFUSE,
            "private data, and the local model can't take it: ask the user, don't upload",
        )
    if not dev.online:
        return (
            (Route.LOCAL, "offline")
            if dev.local_available and fits
            else (Route.REFUSE, "offline, no local fit")
        )
    if not dev.local_available or not fits:
        return Route.CLOUD, "local model unavailable or prompt too long"
    if req.hard:
        return Route.CLOUD, "hard task: bigger model"
    if dev.battery_pct < 20 and not dev.charging:
        return Route.CLOUD, "low battery: save energy"
    return Route.LOCAL, "default: local is faster and free"


def firebase_mode_route(mode: str, nano_available: bool, online: bool) -> Route:
    """Documented semantics of the four Firebase AI Logic hybrid modes."""
    if mode == "ONLY_ON_DEVICE":
        return Route.LOCAL if nano_available else Route.REFUSE
    if mode == "ONLY_IN_CLOUD":
        return Route.CLOUD if online else Route.REFUSE
    if mode == "PREFER_ON_DEVICE":
        return Route.LOCAL if nano_available else (Route.CLOUD if online else Route.REFUSE)
    if mode == "PREFER_IN_CLOUD":
        return Route.CLOUD if online else (Route.LOCAL if nano_available else Route.REFUSE)
    raise ValueError(mode)
