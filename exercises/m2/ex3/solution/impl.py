import json


def _close(prefix: str) -> tuple[str, list[str]]:
    stack: list[str] = []
    in_string = False
    for ch in prefix:
        if in_string:
            if ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "[{":
            stack.append("]" if ch == "[" else "}")
        elif ch in "]}" and stack:
            stack.pop()
    text = prefix + ('"' if in_string else "")
    return text, stack


def parse_partial(prefix: str) -> dict:
    candidate = prefix.strip()
    # Try progressively shorter prefixes until one can be closed into valid JSON.
    while candidate:
        text, stack = _close(candidate)
        body = text.rstrip().rstrip(",:").rstrip()
        try:
            value = json.loads(body + "".join(reversed(stack)))
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            candidate = candidate[:-1]
    return {}
