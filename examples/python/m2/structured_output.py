"""L2.3: structured output with validation and a repair retry.

The model is asked for JSON matching a schema. Whatever comes back is
validated with Pydantic; on failure, the validation error is sent back to the
model as a new user message and we try again (bounded).
"""

from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError

from aincourse import AssistantTurn, ChatModel, Message, ScriptedModel


class Event(BaseModel):
    title: str
    date: str  # ISO 8601, e.g. 2026-11-20
    location: str


SCHEMA = json.dumps(Event.model_json_schema())


def extract_event(model: ChatModel, text: str, max_attempts: int = 3) -> Event:
    messages = [
        Message("system", f"Reply with JSON only, matching this JSON Schema: {SCHEMA}"),
        Message("user", text),
    ]
    last_error = ""
    for _ in range(max_attempts):
        turn = model.complete(messages)
        try:
            return Event.model_validate_json(turn.text)
        except ValidationError as err:
            last_error = str(err)
            messages += [
                turn.as_message(),
                Message("user", f"That JSON was invalid:\n{last_error}\nReturn corrected JSON."),
            ]
    raise ValueError(f"no valid output after {max_attempts} attempts: {last_error}")


def demo_model() -> ScriptedModel:
    # First answer forgets `location`; the second one fixes it after seeing the error.
    return ScriptedModel(
        [
            AssistantTurn(text='{"title": "Rust meetup", "date": "2026-11-20"}'),
            AssistantTurn(
                text='{"title": "Rust meetup", "date": "2026-11-20", "location": "Bengaluru"}'
            ),
        ]
    )


if __name__ == "__main__":
    model = demo_model()
    event = extract_event(model, "Rust meetup on 20 Nov 2026 in Bengaluru")
    print(event, f"(took {len(model.calls)} model calls)")
