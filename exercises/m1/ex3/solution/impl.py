from assess import GATES, Worksheet, sustainable_level


def _missing(ws: Worksheet, level: int) -> list[str]:
    gaps = [c for c in GATES.get(level, ()) if ws.capabilities[c] < 2]
    return sorted(gaps, key=lambda c: (ws.capabilities[c], c))


def next_level_plan(ws: Worksheet) -> list[str]:
    sus = sustainable_level(ws)
    if ws.workflow_level > sus:
        return [f"Stabilise at L{sus}: raise {c} to 2" for c in _missing(ws, ws.workflow_level)]
    target = min(ws.workflow_level + 1, 5)
    gaps = _missing(ws, target)
    if not gaps:
        return [f"Ready for L{target}: run a two-week pilot and measure"]
    return [f"Raise {c} from {ws.capabilities[c]} to 2" for c in gaps]
