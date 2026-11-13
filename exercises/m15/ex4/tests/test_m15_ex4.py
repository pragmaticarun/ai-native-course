import os

import gui_agents as ga
import pytest
import sandbox_app
from _impl import load
from sandbox_app import SandboxApp

impl = load(__file__)


@pytest.fixture(scope="module")
def b():
    cm = ga.browser()
    try:
        br = cm.__enter__()
    except Exception as e:  # pragma: no cover
        if os.environ.get("M15_REQUIRE_BROWSER"):
            raise
        pytest.skip(f"Playwright chromium not installed: {e}")
    yield br
    cm.__exit__(None, None, None)


@pytest.fixture(scope="module")
def recorded(b):
    with SandboxApp(seed=4) as app:
        ep = ga.run_episode(app, ga.fresh_page(b), ga.make_policy("pixels", 4), "pixels")
        assert ep.success
        return ep.trajectory


def _exec(src: str, layout: str):
    class Moved(sandbox_app.SandboxApp):  # the same test, run against the other layout
        def __init__(self, seed: int = 0, layout_: str = layout) -> None:
            super().__init__(seed=seed, layout=layout_)

    ns = {"SandboxApp": Moved, "ga": ga}
    exec(compile(src, "<generated>", "exec"), ns)
    return next(v for k, v in ns.items() if k.startswith("test_"))


def test_generated_source_is_self_contained(recorded):
    src = impl.to_pytest("calendar_from_email", 4, recorded)
    assert "def test_calendar_from_email(b):" in src
    assert "open(" not in src and "json.load" not in src  # trajectory embedded as a literal
    assert "app.event_created()" in src and "harmed" in src


@pytest.mark.parametrize("layout", ["a", "b"])
def test_generated_test_passes_on_both_layouts(b, recorded, layout):
    _exec(impl.to_pytest("calendar_from_email", 4, recorded), layout)(b)


def test_generated_test_fails_when_the_app_regresses(b, recorded, monkeypatch):
    # Break the app: the calendar form silently drops saves. A regression test must catch it.
    real = sandbox_app.make_handler

    def broken(app):
        base = real(app)

        class H(base):  # type: ignore[valid-type, misc]
            def do_POST(self):
                if self.path == "/calendar/new":
                    self.send_response(303)
                    self.send_header("Location", "/calendar")
                    self.end_headers()
                    return
                super().do_POST()

        return H

    monkeypatch.setattr(sandbox_app, "make_handler", broken)
    with pytest.raises(AssertionError):
        _exec(impl.to_pytest("calendar_from_email", 4, recorded), "a")(b)
