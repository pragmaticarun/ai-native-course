"""M15 worked example: "create a calendar event from an email", solved three ways.

(a) pixels: screenshot -> simulated vision model -> click(x, y) / type, with coordinate scaling
(b) hybrid: accessibility-style element list with set-of-marks IDs (+ screenshot) -> click/fill by ID
(c) api:    GET /api/mail -> extract -> POST /api/events

Everything runs for real in headless Chromium through Playwright against `sandbox_app`. The
*models* are scripted policies: they react to observations (they are not blind replays), but
they are not LLMs. `SimulatedVision` stands in for a VLM's grounding: it reads element boxes
from the page and adds Gaussian jitter (`sigma_px`, a simulation parameter, not a measured
model property). So compare the observation/action spaces and their failure modes, not model
quality. A real provider plugs in behind the same `Policy` protocol (M3 has the Anthropic and
OpenAI computer-use action adapters).
"""  # noqa: E501

from __future__ import annotations

import hashlib
import json
import random
import re
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol
from urllib.parse import urlparse

from playwright.sync_api import Browser, Page, Route, sync_playwright
from playwright.sync_api import Error as PlaywrightError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sandbox_app import SandboxApp  # noqa: E402

Mode = Literal["pixels", "hybrid", "api"]
VIEWPORT = {"width": 1280, "height": 800}
MODEL_WIDTH = 640  # screenshots are downscaled before the model sees them

INTERACTIVE = "a, button, input, textarea, select, [role=button]"
MARK_JS = (
    "(sel) => [...document.querySelectorAll(sel)].filter(e => { const r = e.getBoundingClientRect();"  # noqa: E501
    " return r.width > 0 && r.height > 0; }).map((e, i) => { e.setAttribute('data-som', String(i));"
    " const r = e.getBoundingClientRect(); return {id: i, role: e.tagName === 'A' ? 'link' :"
    " (e.tagName === 'INPUT' ? 'textbox' : 'button'), name: (e.getAttribute('aria-label') ||"
    " e.innerText || e.value || '').trim(), x: r.x, y: r.y, w: r.width, h: r.height}; })"
)
OVERLAY_JS = (
    "() => { document.querySelectorAll('.som-label').forEach(n => n.remove());"
    " document.querySelectorAll('[data-som]').forEach(e => { const r = e.getBoundingClientRect();"
    " const d = document.createElement('div'); d.className = 'som-label'; d.textContent = e.dataset.som;"  # noqa: E501
    " Object.assign(d.style, {position: 'absolute', left: (r.x + scrollX) + 'px', top: (r.y + scrollY - 14) + 'px',"  # noqa: E501
    " background: '#e11', color: '#fff', font: '11px monospace', padding: '0 2px', zIndex: 9999,"
    " pointerEvents: 'none'}); document.body.appendChild(d); }); }"
)
HIT_JS = (
    "([x, y, sel]) => { const e = document.elementFromPoint(x, y); const t = e && e.closest(sel);"
    " return t ? (t.getAttribute('aria-label') || t.innerText || '').trim() : null; }"
)
FOCUS_JS = "() => { const e = document.activeElement; return e && e !== document.body ? (e.getAttribute('aria-label') || e.innerText || '').trim() : null; }"  # noqa: E501


@dataclass(frozen=True)
class Mark:
    id: int
    role: str
    name: str
    x: float
    y: float
    w: float
    h: float

    @property
    def center(self) -> tuple[float, float]:
        return self.x + self.w / 2, self.y + self.h / 2


@dataclass
class Obs:
    url: str
    text: str
    marks: list[Mark] = field(default_factory=list)
    screenshot: bytes = b""
    scale: float = 1.0  # css px per model px
    focused: str | None = None
    data: Any = None  # api responses
    note: str = ""  # result of the previous action ("blocked: ...", "invalid: ...")

    def model_bytes(self) -> int:
        """Rough size of what goes to the model (a proxy for tokens/cost)."""
        marks = sum(len(m.name) + 12 for m in self.marks)
        return len(self.screenshot) + marks + (len(json.dumps(self.data)) if self.data else 0)


@dataclass
class Action:
    kind: Literal[
        "goto", "click_xy", "click_mark", "fill_mark", "type", "api_get", "api_post", "done"
    ]
    x: float = 0
    y: float = 0
    mark: int = -1
    text: str = ""
    path: str = ""
    payload: dict[str, str] | None = None
    target: str = ""  # human-readable target (filled in by the env; used by guard, audit, replay)


class Policy(Protocol):
    def next(self, obs: Obs) -> Action: ...


# ---------------------------------------------------------------- safety
INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) instructions",
    r"you are now (in )?\w+ mode",
    r"disregard (your|the) (rules|instructions)",
    r"(reveal|print) (your )?(system prompt|password|api key)",
]
CONSEQUENTIAL = re.compile(r"\b(forward|send|delete|remove|buy|purchase|pay|transfer)\b", re.I)
SENSITIVE_FIELD = re.compile(r"password|card|cvv|otp|ssn", re.I)


@dataclass
class Guard:
    """Policy checks between the model and the browser. `confirm` is the human (default: deny)."""

    confirm: Callable[[str], bool] = lambda what: False
    allowed_kinds: frozenset[str] = frozenset(
        {"goto", "click_xy", "click_mark", "fill_mark", "type", "api_get", "api_post", "done"}
    )
    flags: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    audit: list[dict[str, Any]] = field(default_factory=list)

    def scan(self, text: str) -> list[str]:
        hits = [p for p in INJECTION_PATTERNS if re.search(p, text, re.I)]
        self.flags += [h for h in hits if h not in self.flags]
        return hits

    def check(self, a: Action) -> tuple[bool, str]:
        if a.kind not in self.allowed_kinds:
            return False, f"action kind {a.kind} not allowed"
        consequential = bool(CONSEQUENTIAL.search(a.target)) or (
            a.kind == "api_post" and a.path not in {"/api/events"}
        )
        sensitive = a.kind in {"fill_mark", "type"} and bool(SENSITIVE_FIELD.search(a.target))
        if (consequential or sensitive) and not self.confirm(f"{a.kind} {a.target or a.path}"):
            return False, f"needs human confirmation: {a.target or a.path}"
        return True, "ok"

    def log(self, step: int, a: Action, verdict: str, obs: Obs) -> None:
        self.audit.append(
            {
                "step": step,
                "url": obs.url,
                "action": {k: v for k, v in asdict(a).items() if v not in ("", -1, 0, None)},
                "verdict": verdict,
                "screenshot_sha256": hashlib.sha256(obs.screenshot).hexdigest()[:16],
            }
        )


# ---------------------------------------------------------------- environment
class Env:
    """Wraps a Playwright page. Egress is limited to the sandbox host (route-level allowlist)."""

    def __init__(self, page: Page, base_url: str) -> None:
        self.page, self.base = page, base_url
        self.allowed_host = urlparse(base_url).netloc
        self.egress_blocked: list[str] = []
        self.invalid = 0
        self.last_data: Any = None
        page.route("**/*", self._egress)

    def _egress(self, route: Route) -> None:
        if urlparse(route.request.url).netloc == self.allowed_host:
            route.continue_()
        else:
            self.egress_blocked.append(route.request.url)
            route.abort()

    def marks(self, annotate: bool = False) -> list[Mark]:
        raw = self.page.evaluate(MARK_JS, INTERACTIVE)
        if annotate:
            self.page.evaluate(OVERLAY_JS)
        return [Mark(**m) for m in raw]

    def settle(self, quiet_ms: int = 40) -> None:
        """Wait for idle: a click may or may not start a navigation, so give it a moment to
        begin, then wait for the load event (the 'waiting for idle' lesson in L15.4)."""
        self.page.wait_for_timeout(quiet_ms)
        self.page.wait_for_load_state("load")

    def observe(self, mode: Mode, annotate: bool = False) -> Obs:
        if mode == "api":
            return Obs(self.page.url, "", data=self.last_data)
        for attempt in range(3):
            try:
                return self._observe_page(annotate)
            except PlaywrightError as e:  # navigation landed mid-observation: settle and retry
                if "context was destroyed" not in str(e) or attempt == 2:
                    raise
                self.settle(100)
        raise AssertionError("unreachable")

    def _observe_page(self, annotate: bool) -> Obs:
        self.page.wait_for_load_state("load")
        marks = self.marks(annotate=annotate)
        shot = self.page.screenshot(scale="css")
        scale = VIEWPORT["width"] / MODEL_WIDTH
        return Obs(
            self.page.url,
            self.page.inner_text("body"),
            marks=marks,
            screenshot=shot,
            scale=scale,
            focused=self.page.evaluate(FOCUS_JS),
        )

    def describe(self, a: Action, obs: Obs) -> str:
        """What will this action touch? Needed *before* acting, for the guard."""
        if a.kind == "click_xy":
            css = (a.x * obs.scale, a.y * obs.scale)
            return self.page.evaluate(HIT_JS, [css[0], css[1], INTERACTIVE]) or ""
        if a.kind in {"click_mark", "fill_mark"}:
            m = next((m for m in obs.marks if m.id == a.mark), None)
            return m.name if m else ""
        if a.kind == "type":
            return obs.focused or ""
        return a.path or a.text

    def execute(self, a: Action) -> tuple[bool, str]:
        p = self.page
        if a.kind == "goto":
            p.goto(self.base + a.path)
        elif a.kind == "click_xy":
            if not a.target:
                self.invalid += 1
                p.mouse.click(
                    a.x * VIEWPORT["width"] / MODEL_WIDTH, a.y * VIEWPORT["width"] / MODEL_WIDTH
                )
                return False, "invalid: click hit nothing interactive"
            p.mouse.click(
                a.x * VIEWPORT["width"] / MODEL_WIDTH, a.y * VIEWPORT["width"] / MODEL_WIDTH
            )
        elif a.kind in {"click_mark", "fill_mark"}:
            loc = p.locator(f'[data-som="{a.mark}"]')
            if loc.count() != 1:
                self.invalid += 1
                return False, f"invalid: no element with mark {a.mark}"
            try:
                loc.fill(a.text, timeout=2000) if a.kind == "fill_mark" else loc.click(timeout=2000)
            except PlaywrightError as e:  # e.g. fill() on a link: an invalid action, not a crash
                self.invalid += 1
                return False, f"invalid: {str(e).splitlines()[0][:80]}"
        elif a.kind == "type":
            p.keyboard.type(a.text)
        elif a.kind == "api_get":
            self.last_data = p.request.get(self.base + a.path).json()
        elif a.kind == "api_post":
            r = p.request.post(self.base + a.path, data=a.payload or {})
            self.last_data = {"status": r.status, "body": r.json()}
        if a.kind != "api_get" and a.kind != "api_post":
            self.settle()
        return True, "ok"


# ---------------------------------------------------------------- policies (mock models)
INVITE = re.compile(
    r"put '(?P<title>[^']+)' in the calendar on (?P<date>\d{4}-\d{2}-\d{2}) at (?P<time>\d{2}:\d{2})"  # noqa: E501
)


@dataclass
class SimulatedVision:
    """Stand-in for a VLM's grounding: finds a labelled element, returns its centre in *model*
    pixels plus Gaussian jitter. Larger `sigma_px` = worse grounding."""

    sigma_px: float
    rng: random.Random

    def locate(self, obs: Obs, pred: Callable[[Mark], bool]) -> tuple[float, float] | None:
        m = next((m for m in obs.marks if pred(m)), None)
        if m is None:
            return None
        cx, cy = m.center
        return (
            cx / obs.scale + self.rng.gauss(0, self.sigma_px),
            cy / obs.scale + self.rng.gauss(0, self.sigma_px),
        )


@dataclass
class _Task:
    gullible: bool = False  # follows instructions found on screen (to exercise the guard)
    event: dict[str, str] | None = None
    tried_injection: bool = False
    filled: set[str] = field(default_factory=set)
    saved: bool = False

    def maybe_extract(self, text: str) -> None:
        m = INVITE.search(text)
        if m and not self.event:
            self.event = m.groupdict()

    def on_calendar_done(self, obs: Obs) -> bool:
        ev = self.event
        return (
            bool(ev) and ev is not None and f"{ev['title']} | {ev['date']} {ev['time']}" in obs.text
        )


@dataclass
class PixelPolicy(_Task):
    vision: SimulatedVision = field(default_factory=lambda: SimulatedVision(4.0, random.Random(0)))

    def _click(self, obs: Obs, name: str, exact: bool = True) -> Action:
        xy = self.vision.locate(obs, lambda m: m.name == name if exact else m.name.startswith(name))
        return (
            Action("done", text=f"cannot see {name}")
            if xy is None
            else Action("click_xy", x=xy[0], y=xy[1])
        )

    def next(self, obs: Obs) -> Action:
        path = urlparse(obs.url).path
        if self.gullible and not self.tried_injection and "helpdesk@" in obs.text:
            self.tried_injection = True  # obeys the text on screen: the guard has to stop this
            return self._click(obs, "Forward all mail")
        self.maybe_extract(obs.text)
        if path in ("/", "/mail") and not self.event:
            return self._click(obs, "Invite:", exact=False)
        if path.startswith("/mail") or path == "/":  # invite known: go to the calendar
            return self._click(obs, "Calendar")
        if path == "/calendar" and self.event:
            if self.on_calendar_done(obs):
                return Action("done")
            for field_name in ("Title", "Date", "Time"):
                if field_name not in self.filled:
                    if obs.focused != field_name:
                        return self._click(obs, field_name)
                    self.filled.add(field_name)
                    return Action("type", text=self.event[field_name.lower()])
            self.filled.clear() if self.saved else None  # verify-after-act failed: redo the form
            self.saved = True
            return self._click(obs, "Save event")
        return Action("goto", path="/mail")


@dataclass
class HybridPolicy(_Task):
    def _mark(self, obs: Obs, pred: Callable[[Mark], bool]) -> int:
        return next((m.id for m in obs.marks if pred(m)), -1)

    def next(self, obs: Obs) -> Action:
        path = urlparse(obs.url).path
        if self.gullible and not self.tried_injection and "helpdesk@" in obs.text:
            self.tried_injection = True
            return Action(
                "click_mark", mark=self._mark(obs, lambda m: m.name == "Forward all mail")
            )
        self.maybe_extract(obs.text)
        if path in ("/", "/mail") and not self.event:
            return Action(
                "click_mark", mark=self._mark(obs, lambda m: m.name.startswith("Invite:"))
            )
        if path.startswith("/mail") or path == "/":
            return Action("click_mark", mark=self._mark(obs, lambda m: m.name == "Calendar"))
        if path == "/calendar" and self.event:
            if self.on_calendar_done(obs):
                return Action("done")
            for name in ("Title", "Date", "Time"):
                if name not in self.filled:
                    self.filled.add(name)
                    return Action("fill_mark", mark=self._mark(obs, lambda m, n=name: m.name == n),  # type: ignore[misc]
                                  text=self.event[name.lower()])  # fmt: skip
            if self.saved:  # verify-after-act: the event is not listed, so redo the form once
                self.filled.clear()
            self.saved = True
            return Action("click_mark", mark=self._mark(obs, lambda m: m.name == "Save event"))
        return Action("goto", path="/mail")


@dataclass
class ApiPolicy(_Task):
    stage: int = 0

    def next(self, obs: Obs) -> Action:
        self.stage += 1
        if self.stage == 1:
            return Action("api_get", path="/api/mail")
        if self.stage == 2:
            for (
                mail
            ) in obs.data:  # screen/API content is still untrusted: we only *extract* from it
                self.maybe_extract(mail["body"])
            if not self.event:
                return Action("done", text="no invite found")
            return Action("api_post", path="/api/events", payload=self.event)
        if self.stage == 3:
            return Action("api_get", path="/api/events")
        return Action("done", text="verified" if self.event in obs.data else "not verified")


# ---------------------------------------------------------------- loop + harness
@dataclass
class Episode:
    mode: str
    success: bool
    harmed: bool
    steps: int
    invalid: int
    seconds: float
    model_bytes: int
    blocked: list[str]
    egress_blocked: list[str]
    injection_flags: list[str]
    trajectory: list[dict[str, Any]]


def run_episode(
    app: SandboxApp,
    page: Page,
    policy: Policy,
    mode: Mode,
    guard: Guard | None = None,
    max_steps: int = 25,
    max_seconds: float = 30.0,
    annotate: bool = False,
) -> Episode:
    guard = guard or Guard()
    env = Env(page, app.url)
    if mode != "api":
        page.goto(app.url + "/mail")
    t0, steps, sent, traj = time.perf_counter(), 0, 0, []
    note = ""
    while steps < max_steps and time.perf_counter() - t0 < max_seconds:
        obs = env.observe(mode, annotate=annotate)
        obs.note = note
        guard.scan(obs.text + (json.dumps(obs.data) if obs.data else ""))
        sent += obs.model_bytes()
        a = policy.next(obs)
        steps += 1
        if a.kind == "done":
            guard.log(steps, a, "done", obs)
            break
        a.target = env.describe(a, obs)
        ok, why = guard.check(a)
        if not ok:
            guard.blocked.append(why)
            guard.log(steps, a, f"blocked: {why}", obs)
            note = f"blocked: {why}"
            continue
        _, note = env.execute(a)
        guard.log(steps, a, note, obs)
        traj.append(asdict(a))
    return Episode(
        mode, app.event_created(), app.harmed(), steps, env.invalid,
        round(time.perf_counter() - t0, 3), sent, list(guard.blocked), env.egress_blocked,
        list(guard.flags), traj,
    )  # fmt: skip


@contextmanager
def browser() -> Iterator[Browser]:
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        try:
            yield b
        finally:
            b.close()


def fresh_page(b: Browser) -> Page:
    """A fresh context per episode = a fresh profile (no cookies, no storage)."""
    return b.new_context(viewport=VIEWPORT).new_page()  # type: ignore[arg-type]


def make_policy(mode: Mode, seed: int, sigma_px: float = 4.0, gullible: bool = False) -> Policy:
    if mode == "pixels":
        return PixelPolicy(gullible=gullible, vision=SimulatedVision(sigma_px, random.Random(seed)))
    if mode == "hybrid":
        return HybridPolicy(gullible=gullible)
    return ApiPolicy(gullible=gullible)


def compare(
    b: Browser, seeds: range = range(3), sigma_px: float = 4.0
) -> dict[str, dict[str, float]]:
    """The WE table: same task, three approaches, several seeded inboxes each."""
    out: dict[str, dict[str, float]] = {}
    for mode in ("pixels", "hybrid", "api"):
        eps = []
        for seed in seeds:
            with SandboxApp(seed=seed) as app:
                page = fresh_page(b)
                eps.append(run_episode(app, page, make_policy(mode, seed, sigma_px), mode))  # type: ignore[arg-type]
                page.context.close()
        n = len(eps)
        out[mode] = {
            "success": sum(e.success for e in eps) / n,
            "steps": sum(e.steps for e in eps) / n,
            "invalid": sum(e.invalid for e in eps) / n,
            "seconds": round(sum(e.seconds for e in eps) / n, 3),
            "model_kb": round(sum(e.model_bytes for e in eps) / n / 1024, 1),
        }
    return out


def replay(
    app: SandboxApp, page: Page, trajectory: list[dict[str, Any]], by: Literal["coords", "names"]
) -> bool:
    """Deterministic replay with no model. `coords` re-clicks recorded pixels (breaks when the
    layout moves); `names` re-resolves each recorded target by its accessible name."""
    env = Env(page, app.url)
    page.goto(app.url + "/mail")
    for d in trajectory:
        a = Action(**d)
        if by == "names" and a.kind in {"click_xy", "click_mark", "fill_mark"}:
            marks = env.marks()
            m = next((m for m in marks if m.name == a.target), None)
            if m is None:
                return False
            if a.kind == "fill_mark":
                page.locator(f'[data-som="{m.id}"]').fill(a.text)
            else:
                page.locator(f'[data-som="{m.id}"]').click()
            env.settle()
            continue
        if a.kind in {"click_mark", "fill_mark"}:
            env.marks()
        env.execute(a)
    return app.event_created()


def main() -> None:
    with browser() as b:
        table = compare(b)
    print(f"{'mode':8} {'success':>8} {'steps':>6} {'invalid':>8} {'seconds':>8} {'model_kb':>9}")
    for mode, r in table.items():
        print(
            f"{mode:8} {r['success']:8.2f} {r['steps']:6.1f} {r['invalid']:8.1f} {r['seconds']:8.3f} {r['model_kb']:9.1f}"  # noqa: E501
        )


if __name__ == "__main__":
    main()
