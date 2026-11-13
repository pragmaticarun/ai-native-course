"""P8 milestone 2: three model adapters, one internal action type.

* Anthropic `computer_toolset_20260801`: the model's turn is a list of member `tool_use` blocks
  (`"toolset_name": "computer"`, e.g. `left_click` with `input.coordinate`), possibly several
  (a batch). We answer every block with a `tool_result` that echoes `toolset_name`; after the
  first failure the rest get the documented halt text.
* OpenAI Responses `computer` tool: `computer_call` items with an ordered `actions` list
  (`click`, `type`, `keypress`, `wait`, `screenshot`, ...); we answer with a
  `computer_call_output` carrying a `computer_screenshot`. The SDK's `before_action` hook is the
  same idea as our `guard` node.
* Vendor-neutral: the graph's own JSON action schema over set-of-marks ids, for any model.

Formats follow the vendors' docs as read on 14 Nov 2026 (links on the project page). The
adapters are tested against recorded payloads only; they have NOT been run against live APIs.
`encode` exists so the scripted planner can produce realistic turns for the recordings.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import jsonschema
from p8_kit import WEB_MODEL_W, Action, Obs, Step

HALT_TEXT = "Not executed: an earlier computer action in this turn failed."


class AdapterError(ValueError):
    """The model asked for something this adapter can't map: an invalid action."""


@dataclass
class Decoded:
    actions: list[tuple[str, Action]]  # (call reference, action)
    done: bool = False
    answer: str = ""


def _center_model_px(obs: Obs, name: str, slip: bool) -> tuple[int, int]:
    m = obs.mark(name)
    if m is None:
        raise AdapterError(f"planner referred to a missing element {name!r}")
    cx, cy = m.center
    x, y = round(cx / obs.scale), round(cy / obs.scale)
    if slip:  # simulated grounding error: lands in empty space at the right edge
        x = (WEB_MODEL_W if obs.env == "web" else 540) - 3
    return x, y


# --------------------------------------------------------------------------- Anthropic
class AnthropicAdapter:
    name = "anthropic"
    pixel = True

    def decode(self, turn: dict[str, Any]) -> Decoded:
        out: list[tuple[str, Action]] = []
        texts: list[str] = []
        for b in turn.get("content", []):
            if b.get("type") == "text":
                texts.append(b["text"])
                continue
            if b.get("type") != "tool_use" or b.get("toolset_name") != "computer":
                continue
            name, inp = b["name"], b.get("input", {})
            if name == "left_click" and "coordinate" in inp:
                out.append(
                    (b["id"], Action("click", xy=(inp["coordinate"][0], inp["coordinate"][1])))
                )
            elif name == "type":
                out.append((b["id"], Action("type", text=inp["text"])))
            elif name == "key":
                out.append((b["id"], Action("key", text=inp["text"])))
            elif name in ("screenshot", "wait"):
                out.append((b["id"], Action("wait")))
            else:
                raise AdapterError(f"member {name!r} not supported")
        return Decoded(out, done=not out, answer=" ".join(texts))

    def encode(
        self, steps: list[Step], obs: Obs, slip: Callable[[], bool], turn_no: int
    ) -> dict[str, Any]:
        blocks: list[dict[str, Any]] = []

        def use(name: str, inp: dict[str, Any]) -> None:
            blocks.append(
                {
                    "type": "tool_use",
                    "id": f"toolu_{turn_no:03d}_{len(blocks)}",
                    "name": name,
                    "toolset_name": "computer",
                    "input": inp,
                }
            )

        for s in steps:
            if s.op == "done":
                return {"content": [{"type": "text", "text": s.text}]}
            if s.op == "back":
                use("key", {"text": "Back"})
                continue
            use("left_click", {"coordinate": list(_center_model_px(obs, s.name, slip()))})
            if s.op == "fill":
                if obs.env == "web":
                    use("key", {"text": "ctrl+a"})
                use("type", {"text": s.text})
        use("screenshot", {})
        return {"content": blocks}

    def results(
        self, decoded: Decoded, outcomes: list[tuple[bool, str]], screenshot_b64: str
    ) -> list[dict[str, Any]]:
        res: list[dict[str, Any]] = []
        for i, (ref, _a) in enumerate(decoded.actions):
            r: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": ref,
                "toolset_name": "computer",
            }
            if i < len(outcomes):
                ok, note = outcomes[i]
                r["content"] = [{"type": "text", "text": "OK"}] if ok else note
                if not ok:
                    r["is_error"] = True
            else:
                r.update(content=HALT_TEXT, is_error=True)
            res.append(r)
        if res and isinstance(res[-1].get("content"), list):
            res[-1]["content"].append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64},
                }
            )
        return res


# --------------------------------------------------------------------------- OpenAI
class OpenAIAdapter:
    name = "openai"
    pixel = True

    def decode(self, turn: dict[str, Any]) -> Decoded:
        out: list[tuple[str, Action]] = []
        texts: list[str] = []
        for item in turn.get("output", []):
            if item.get("type") == "message":
                texts += [
                    c["text"] for c in item.get("content", []) if c.get("type") == "output_text"
                ]
            if item.get("type") != "computer_call":
                continue
            for a in item["actions"]:
                t = a["type"]
                if t == "click" and a.get("button", "left") == "left":
                    out.append((item["call_id"], Action("click", xy=(a["x"], a["y"]))))
                elif t == "type":
                    out.append((item["call_id"], Action("type", text=a["text"])))
                elif t == "keypress":
                    out.append((item["call_id"], Action("key", text="+".join(a["keys"]))))
                elif t in ("wait", "screenshot"):
                    out.append((item["call_id"], Action("wait")))
                else:
                    raise AdapterError(f"action {t!r} not supported")
        return Decoded(out, done=not out, answer=" ".join(texts))

    def encode(
        self, steps: list[Step], obs: Obs, slip: Callable[[], bool], turn_no: int
    ) -> dict[str, Any]:
        actions: list[dict[str, Any]] = []
        for s in steps:
            if s.op == "done":
                return {
                    "output": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": s.text}],
                        }
                    ]
                }
            if s.op == "back":
                actions.append({"type": "keypress", "keys": ["Back"]})
                continue
            x, y = _center_model_px(obs, s.name, slip())
            actions.append({"type": "click", "button": "left", "x": x, "y": y})
            if s.op == "fill":
                if obs.env == "web":
                    actions.append({"type": "keypress", "keys": ["CTRL", "A"]})
                actions.append({"type": "type", "text": s.text})
        actions.append({"type": "screenshot"})
        return {
            "output": [
                {
                    "type": "computer_call",
                    "call_id": f"call_{turn_no:03d}",
                    "actions": actions,
                    "status": "completed",
                }
            ]
        }

    def results(
        self, decoded: Decoded, outcomes: list[tuple[bool, str]], screenshot_b64: str
    ) -> list[dict[str, Any]]:
        call_ids = list(dict.fromkeys(ref for ref, _ in decoded.actions))
        res: list[dict[str, Any]] = [
            {
                "type": "computer_call_output",
                "call_id": c,
                "output": {
                    "type": "computer_screenshot",
                    "image_url": f"data:image/png;base64,{screenshot_b64}",
                    "detail": "original",
                },
            }
            for c in call_ids
        ]
        problems = [note for ok, note in outcomes if not ok]
        if problems or len(outcomes) < len(decoded.actions):
            res.append(
                {
                    "role": "user",
                    "content": "Some actions did not run: " + "; ".join(problems or [HALT_TEXT]),
                }
            )
        return res


# --------------------------------------------------------------------------- neutral
NEUTRAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["actions"],
    "properties": {
        "actions": {
            "type": "array",
            "minItems": 1,
            "items": {
                "oneOf": [
                    {
                        "type": "object",
                        "required": ["action", "mark"],
                        "additionalProperties": False,
                        "properties": {"action": {"const": "click"}, "mark": {"type": "integer"}},
                    },
                    {
                        "type": "object",
                        "required": ["action", "mark", "text"],
                        "additionalProperties": False,
                        "properties": {
                            "action": {"const": "type"},
                            "mark": {"type": "integer"},
                            "text": {"type": "string"},
                        },
                    },
                    {
                        "type": "object",
                        "required": ["action", "key"],
                        "additionalProperties": False,
                        "properties": {"action": {"const": "key"}, "key": {"type": "string"}},
                    },
                    {
                        "type": "object",
                        "required": ["action", "answer"],
                        "additionalProperties": False,
                        "properties": {"action": {"const": "done"}, "answer": {"type": "string"}},
                    },
                ]
            },
        }
    },
}


class NeutralAdapter:
    name = "neutral"
    pixel = False

    def decode(self, turn: dict[str, Any]) -> Decoded:
        try:
            jsonschema.validate(turn, NEUTRAL_SCHEMA)
        except jsonschema.ValidationError as e:
            raise AdapterError(f"schema: {e.message}") from e
        out: list[tuple[str, Action]] = []
        for i, a in enumerate(turn["actions"]):
            if a["action"] == "done":
                return Decoded(out, done=True, answer=a["answer"])
            if a["action"] == "click":
                out.append((str(i), Action("click", mark=a["mark"])))
            elif a["action"] == "type":
                out.append((str(i), Action("type", mark=a["mark"], text=a["text"])))
            else:
                out.append((str(i), Action("key", text=a["key"])))
        return Decoded(out)

    def encode(
        self, steps: list[Step], obs: Obs, slip: Callable[[], bool], turn_no: int
    ) -> dict[str, Any]:
        acts: list[dict[str, Any]] = []
        for s in steps:
            if s.op == "done":
                acts.append({"action": "done", "answer": s.text})
                break
            if s.op == "back":
                acts.append({"action": "key", "key": "Back"})
                continue
            m = obs.mark(s.name)
            if m is None:
                raise AdapterError(f"planner referred to a missing element {s.name!r}")
            mark = 999 if s.op == "click" and slip() else m.id  # simulated grounding error
            acts.append(
                {"action": "click", "mark": mark}
                if s.op == "click"
                else {"action": "type", "mark": mark, "text": s.text}
            )
        return {"actions": acts}

    def results(
        self, decoded: Decoded, outcomes: list[tuple[bool, str]], screenshot_b64: str
    ) -> list[dict[str, Any]]:
        res = [
            {"ref": ref, "ok": o[0], "note": o[1]}
            for (ref, _), o in zip(decoded.actions, outcomes, strict=False)
        ]
        res += [
            {"ref": ref, "ok": False, "note": "not executed"}
            for ref, _ in decoded.actions[len(outcomes) :]
        ]
        return res


ADAPTERS: dict[str, Any] = {
    "anthropic": AnthropicAdapter(),
    "openai": OpenAIAdapter(),
    "neutral": NeutralAdapter(),
}
