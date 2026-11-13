"""M15 L15.3/L15.4: mobile-use on Android with adb + uiautomator, against a *fake device*.

`FakeAndroid` answers the same adb argv the real `AdbDevice` (M3) sends: `uiautomator dump`,
`exec-out cat`, `input tap|text|keyevent`, `am start`, `am force-stop`. Screens are
hand-written XML in `uiautomator dump` format (fixtures/android_*.xml, synthetic). So the agent
loop, set-of-marks, coordinate scaling, idle detection, recovery and the injection guard are
tested; **nothing here has run on a real device or emulator (untested)**, and AndroidWorld was
not run.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "m3")]
from gui_agents import Action, Guard  # noqa: E402
from mobile_adb import AdbDevice, UiNode, render_for_model  # noqa: E402

FIX = HERE / "fixtures"
CAL = "com.example.calendar"


def scale_to_device(
    xy: tuple[float, float], model_wh: tuple[int, int], device_wh: tuple[int, int]
) -> tuple[int, int]:
    """Model saw a downscaled screenshot; map its point back to device pixels."""
    return round(xy[0] * device_wh[0] / model_wh[0]), round(xy[1] * device_wh[1] / model_wh[1])


@dataclass
class FakeAndroid:
    """A tiny state machine standing in for a phone. Records every adb argv it receives."""

    screen: str = "home"
    fields: dict[str, str] = field(default_factory=lambda: {"Title": "", "Date": "", "Time": ""})
    focused: str | None = None
    events: list[str] = field(default_factory=list)
    deleted_all: bool = False
    calls: list[list[str]] = field(default_factory=list)
    settle_dumps: int = 0  # how many dumps the UI is still animating for after a transition

    def xml(self) -> str:
        if self.settle_dumps:  # mid-animation: a spinner instead of content
            self.settle_dumps -= 1
            return '<hierarchy><node text="Loading" clickable="false" bounds="[0,0][1080,2400]"/></hierarchy>'  # noqa: E501
        return self.content()

    def content(self) -> str:
        x = (FIX / f"android_{self.screen}.xml").read_text()
        for k, v in self.fields.items():
            x = x.replace(
                f'text="" resource-id="{CAL}:id/{k.lower()}"',
                f'text="{v}" resource-id="{CAL}:id/{k.lower()}"',
            )
        rows = "".join(
            f'<node text="{e}" resource-id="{CAL}:id/row" clickable="false" bounds="[40,{400 + 120 * i}][1040,{500 + 120 * i}]"/>'  # noqa: E501
            for i, e in enumerate(self.events)
        )
        return x.replace("<!--EVENTS-->", rows)

    def _go(self, screen: str) -> None:
        self.screen, self.focused, self.settle_dumps = screen, None, 1

    def __call__(self, args: Sequence[str]) -> bytes:
        a = list(args)
        self.calls.append(a)
        if a[:3] == ["shell", "uiautomator", "dump"]:
            return b"UI hierchary dumped to: /sdcard/ui.xml"
        if a[:2] == ["exec-out", "cat"]:
            return self.xml().encode()
        if a[:3] == ["shell", "input", "tap"]:
            self._tap(int(a[3]), int(a[4]))
        elif a[:3] == ["shell", "input", "text"] and self.focused:
            self.fields[self.focused] += a[3].replace("%s", " ")
        elif a[:3] == ["shell", "input", "keyevent"]:
            self._go(
                {
                    "KEYCODE_BACK": "calendar" if self.screen == "form" else "home",
                    "KEYCODE_HOME": "home",
                }[a[3]]
            )
        elif a[:3] == ["shell", "am", "start"]:
            self._go("calendar")
        elif a[:3] == ["shell", "am", "force-stop"]:
            self._go("home")
        return b""

    def _tap(self, x: int, y: int) -> None:
        hit = next(
            (el for el in _nodes_with_bounds(self.content())
             if el[2] and el[1][0] <= x <= el[1][2] and el[1][1] <= y <= el[1][3]),
            None,
        )  # fmt: skip
        if hit is None:
            return
        label, _, _ = hit
        if label.startswith("Invite:") or label == "Calendar":
            self._go("calendar")
        elif label == "New event":
            self._go("form")
        elif label in self.fields:
            self.focused = label
        elif label == "Save":
            self.events.append(
                f"{self.fields['Title']} {self.fields['Date']} {self.fields['Time']}"
            )
            self.fields = {k: "" for k in self.fields}
            self._go("calendar")
        elif label == "Delete all":
            self.deleted_all = True


def _nodes_with_bounds(xml: str) -> list[tuple[str, tuple[int, int, int, int], bool]]:
    out: list[tuple[str, tuple[int, int, int, int], bool]] = []
    for m in re.finditer(r"<node ([^>]*?)/?>", xml):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        b = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", attrs.get("bounds", ""))
        if b:
            label = attrs.get("content-desc") or attrs.get("text", "")
            x1, y1, x2, y2 = (int(v) for v in b.groups())
            out.append((label, (x1, y1, x2, y2), attrs.get("clickable") == "true"))
    return out


def wait_for_idle(
    dev: AdbDevice, max_dumps: int = 6, busy: tuple[str, ...] = ("Loading",)
) -> list[UiNode]:
    """Idle = two consecutive identical UI dumps *and* no busy indicator on screen.
    (Two identical spinner frames are not idle: the test for this exists because the first
    version of this function got it wrong.)"""
    prev = dev.ui_tree()
    for _ in range(max_dumps):
        cur = dev.ui_tree()
        if cur == prev and not any(n.text in busy for n in cur):
            return cur
        prev = cur
    raise TimeoutError("UI never settled")


def recover(dev: AdbDevice, level: int) -> str:
    """Escalating recovery: back -> home -> relaunch the app (force-stop + am start)."""
    if level == 0:
        dev.key("KEYCODE_BACK")
        return "back"
    if level == 1:
        dev.key("KEYCODE_HOME")
        return "home"
    dev._adb("shell", "am", "force-stop", CAL)
    dev._adb("shell", "am", "start", "-n", f"{CAL}/.MainActivity")
    return "relaunch"


INVITE = re.compile(r"Invite: (?P<title>.+?) (?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{2}:\d{2})")


@dataclass
class MobileResult:
    success: bool
    steps: int
    blocked: list[str]
    flags: list[str]
    recoveries: list[str]


def create_event_from_notification(dev: AdbDevice, fake: FakeAndroid, guard: Guard, gullible: bool = False,  # noqa: E501
                                   max_steps: int = 20) -> MobileResult:  # fmt: skip
    """Scripted policy over set-of-marks nodes; every tap goes through the guard."""
    want: dict[str, str] | None = None
    recoveries: list[str] = []
    steps = 0
    tried_injection = False
    typed: set[str] = set()
    while steps < max_steps:
        steps += 1
        nodes = wait_for_idle(dev)
        text = render_for_model(nodes)
        guard.scan(text)
        by = {n.text: n for n in nodes}
        if want is None:
            m = next((INVITE.search(n.text) for n in nodes if INVITE.search(n.text)), None)
            want = m.groupdict() if m else None
        if gullible and not tried_injection and "Delete all" in by:
            tried_injection = True
            a = Action("click_mark", mark=by["Delete all"].mark, target="Delete all")
            ok, why = guard.check(a)
            if not ok:
                guard.blocked.append(why)
                continue
            dev.tap(by["Delete all"])
            continue
        if want and any(n.text == f"{want['title']} {want['date']} {want['time']}" for n in nodes):
            return MobileResult(True, steps, guard.blocked, guard.flags, recoveries)
        if fake.screen == "home":
            target = next((n for n in nodes if n.text.startswith("Invite:")), None) or by.get(
                "Calendar"
            )
            if target is None:
                recoveries.append(recover(dev, len(recoveries)))
                continue
            dev.tap(target)
        elif fake.screen == "calendar":
            dev.tap(by["New event"])
        elif fake.screen == "form" and want:
            todo = [k for k in ("Title", "Date", "Time") if k not in typed]
            if todo:
                field_node = next(n for n in nodes if n.resource_id.endswith(todo[0].lower()))
                dev.tap(field_node)
                dev.type_text(want[todo[0].lower()])
                typed.add(todo[0])
            else:
                dev.tap(by["Save"])
        else:
            recoveries.append(recover(dev, len(recoveries)))
    return MobileResult(False, steps, guard.blocked, guard.flags, recoveries)
