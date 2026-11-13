import json


def parse_partial(prefix: str) -> dict:
    # TODO: complete the prefix so json.loads accepts it.
    try:
        return json.loads(prefix)
    except json.JSONDecodeError:
        return {}
