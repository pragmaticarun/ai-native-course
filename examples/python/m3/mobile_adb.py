"""L3 worked example (mobile-use): observe and act on Android with plain `adb`.

Observation: `adb exec-out screencap -p` (PNG) and `uiautomator dump` (XML
accessibility tree). Action: `adb shell input tap|text|keyevent`.

UNTESTED ON A DEVICE/EMULATOR in this milestone: CI only runs the parsing and
command-building logic against a fake runner and a hand-written XML fixture.
Running it for real needs `adb` and a booted emulator (see M15).
"""

from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from dataclasses import dataclass

Runner = Callable[[Sequence[str]], bytes]


def subprocess_runner(args: Sequence[str]) -> bytes:
    return subprocess.run(["adb", *args], check=True, capture_output=True).stdout


@dataclass(frozen=True)
class UiNode:
    mark: int  # set-of-marks id shown to the model instead of raw coordinates
    text: str
    resource_id: str
    clickable: bool
    center: tuple[int, int]


_BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def parse_ui(xml: str) -> list[UiNode]:
    """Keep only nodes a user could act on or read, and give them stable marks."""
    nodes: list[UiNode] = []
    for el in ET.fromstring(xml).iter("node"):
        text = el.get("text") or el.get("content-desc") or ""
        clickable = el.get("clickable") == "true"
        if not (clickable or text):
            continue
        m = _BOUNDS.match(el.get("bounds", ""))
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        nodes.append(
            UiNode(
                len(nodes) + 1,
                text,
                el.get("resource-id", ""),
                clickable,
                ((x1 + x2) // 2, (y1 + y2) // 2),
            )
        )
    return nodes


def render_for_model(nodes: list[UiNode]) -> str:
    return "\n".join(f"[{n.mark}] {'button' if n.clickable else 'text'} {n.text!r}" for n in nodes)


class AdbDevice:
    def __init__(self, run: Runner = subprocess_runner, serial: str | None = None) -> None:
        self._run = run
        self._prefix = ["-s", serial] if serial else []

    def _adb(self, *args: str) -> bytes:
        return self._run([*self._prefix, *args])

    def screenshot_png(self) -> bytes:
        return self._adb("exec-out", "screencap", "-p")

    def ui_tree(self) -> list[UiNode]:
        self._adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
        return parse_ui(self._adb("exec-out", "cat", "/sdcard/ui.xml").decode())

    def tap(self, node: UiNode) -> None:
        self._adb("shell", "input", "tap", str(node.center[0]), str(node.center[1]))

    def type_text(self, text: str) -> None:
        # `input text` treats spaces specially; %s is the documented-in-practice escape.
        self._adb("shell", "input", "text", text.replace(" ", "%s"))

    def key(self, keycode: str) -> None:
        self._adb("shell", "input", "keyevent", keycode)


if __name__ == "__main__":  # needs a real device or emulator
    device = AdbDevice()
    print(render_for_model(device.ui_tree()))
