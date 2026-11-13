def to_pytest(name: str, seed: int, trajectory: list[dict]) -> str:
    # TODO: replays raw coordinates and asserts nothing about state
    return f"""
def test_{name}(b):
    with SandboxApp(seed={seed}) as app:
        page = ga.fresh_page(b)
        ga.replay(app, page, {trajectory!r}, "coords")
"""
