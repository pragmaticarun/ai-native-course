import json


def load(path):
    try:
        return json.load(open(path))
    except ValueError as e:
        raise ValueError(f"bad JSON in {path}") from e
