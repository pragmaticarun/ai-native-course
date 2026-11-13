def normalize_tags(tags: list[str]) -> list[str]:
    """Lower-case, strip, drop empty, de-duplicate, sort."""
    return sorted({t.strip().lower() for t in tags if t.strip()})
