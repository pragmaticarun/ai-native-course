import pprint


def _clean(step: dict) -> dict:
    s = dict(step)
    if s.get("target"):
        s["x"], s["y"] = 0, 0
    return s


def to_pytest(name: str, seed: int, trajectory: list[dict]) -> str:
    steps = [_clean(s) for s in trajectory if s.get("kind") != "done"]
    traj = pprint.pformat(steps, width=100, sort_dicts=True)
    body = "\n".join("    " + line for line in f"TRAJ = {traj}".splitlines())
    return f"""
def test_{name}(b):
{body}
    with SandboxApp(seed={seed}) as app:
        page = ga.fresh_page(b)
        assert ga.replay(app, page, TRAJ, "names")
        assert app.event_created()
        assert not app.harmed()
"""
