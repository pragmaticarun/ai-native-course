"""M14 L14.3: GStreamer pipelines as agent tools: parse -> allowlist -> sandboxed run.

The model proposes a `gst-launch-1.0`-style description. We never hand that string to
a shell. `parse()` splits it into elements (`!` links), properties (`key=value`), caps
filters (`video/x-raw,width=320`) and named-pad references (`t.`, `mux.`); `validate()`
checks every element against an allowlist and every file property against the sandbox
root; `run()` executes the parsed argv (no shell) with a timeout, `-e` for a clean EOS,
and returns the bus messages gst-launch prints as observations.

`run()` needs `gst-launch-1.0` on PATH: CI apt-installs Ubuntu's GStreamer for it; the box
used Debian's. Neither is 1.28, so the ML elements (`onnxinference`, `tensordecodebin`) are
in the allowlist/validator but have **not** been run (untested).
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ALLOWED = {
    # sources (bounded) and sinks
    "videotestsrc", "audiotestsrc", "filesrc", "filesink", "fakesink", "appsink",
    # plumbing
    "queue", "tee", "capsfilter", "identity",
    # conversion / scaling
    "videoconvert", "videoscale", "videorate", "audioconvert", "audioresample",
    # codecs / containers present in -base/-good
    "decodebin", "jpegenc", "pngenc", "wavenc", "matroskamux", "qtdemux", "oggmux",
    "vorbisenc", "theoraenc",
    # analytics
    "level",
    # GStreamer 1.28 ML inference (allowlisted, untested here)
    "onnxinference", "tensordecodebin",
}  # fmt: skip
FILE_PROPS = {"location"}
BANNED_PROPS = {"uri", "command", "exec"}
BANNED_ELEMENTS_HINT = {"souphttpsrc", "udpsink", "tcpserversink", "rtspsrc", "filesrc-uri"}


class PipelineError(ValueError):
    pass


@dataclass
class Element:
    factory: str
    props: dict[str, str] = field(default_factory=dict)


@dataclass
class Pipeline:
    branches: list[list[Element | str]]  # str = caps filter or pad reference like "t."

    def elements(self) -> list[Element]:
        return [x for b in self.branches for x in b if isinstance(x, Element)]


_CAPS = re.compile(r"^[a-z]+/[a-z0-9.+-]+(,.*)?$", re.I)
_PADREF = re.compile(r"^[A-Za-z_][\w-]*\.([\w%-]*)$")


def parse(desc: str) -> Pipeline:
    tokens = shlex.split(desc)
    if not tokens:
        raise PipelineError("empty pipeline")
    branches: list[list[Element | str]] = [[]]
    for tok in tokens:
        if tok == "!":
            continue
        cur = branches[-1]
        if _PADREF.match(tok) and "=" not in tok:
            if cur and not (isinstance(cur[-1], str) and cur[-1].endswith(".")):
                branches.append([tok])  # `t.` starts a new branch from tee `t`
            else:
                cur.append(tok)
        elif _CAPS.match(tok):
            cur.append(tok)
        elif "=" in tok:
            if not cur or not isinstance(cur[-1], Element):
                raise PipelineError(f"property {tok!r} has no element")
            k, v = tok.split("=", 1)
            cur[-1].props[k] = v
        elif re.match(r"^[a-z][a-z0-9_-]*$", tok):
            cur.append(Element(tok))
        else:
            raise PipelineError(f"unrecognised token {tok!r}")
    return Pipeline(branches)


def validate(p: Pipeline, root: Path, allowed: set[str] = ALLOWED) -> list[str]:
    """Return problems (empty = OK). Bounded sources must have num-buffers set."""
    probs = []
    for el in p.elements():
        if el.factory not in allowed:
            probs.append(f"element not allowed: {el.factory}")
        for k, v in el.props.items():
            if k in BANNED_PROPS:
                probs.append(f"{el.factory}: property {k} not allowed")
            if k in FILE_PROPS:
                if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", v) or v.startswith("/"):
                    probs.append(f"{el.factory}: location must be relative: {v}")
                elif not (root / v).resolve().is_relative_to(root.resolve()):
                    probs.append(f"{el.factory}: location escapes sandbox: {v}")
        if el.factory in {"videotestsrc", "audiotestsrc"} and "num-buffers" not in el.props:
            probs.append(f"{el.factory}: set num-buffers so the pipeline ends")
    return probs


def have_gst() -> bool:
    return shutil.which("gst-launch-1.0") is not None


@dataclass
class RunResult:
    ok: bool
    messages: list[str]
    timed_out: bool = False


def to_argv(p: Pipeline) -> list[str]:
    out: list[str] = []
    for branch in p.branches:
        prev_link = False
        for x in branch:
            if isinstance(x, Element):
                if prev_link:
                    out.append("!")
                out.append(x.factory)
                out += [f"{k}={v}" for k, v in x.props.items()]
                prev_link = True
            else:
                if x.endswith("."):  # pad reference
                    out.append(x)
                    prev_link = True
                else:  # caps
                    out += ["!", x]
                    prev_link = True
    return out


def run(desc: str, root: Path, timeout: float = 20.0) -> RunResult:
    p = parse(desc)
    probs = validate(p, root)
    if probs:
        raise PipelineError("; ".join(probs))
    argv = ["gst-launch-1.0", "-e", "-m", *to_argv(p)]
    try:
        proc = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return RunResult(False, [], timed_out=True)
    msgs = [ln.strip() for ln in (proc.stdout + proc.stderr).splitlines() if "Got message" in ln]
    return RunResult(proc.returncode == 0, msgs)


def level_peaks(messages: list[str]) -> list[float]:
    """Pull `peak` dB values out of `level` element bus messages (observation for an agent).

    1.28 prints `peak=(GValueArray)< -6.02 >`; older releases print `peak=(double){ -6.02 }`."""
    vals = []
    for m in messages:
        for grp in re.findall(r"peak=\((?:double|GValueArray)\)[{<]\s*([-\d.e ,]+)[}>]", m):
            vals += [float(x) for x in grp.split(",")]
    return vals
