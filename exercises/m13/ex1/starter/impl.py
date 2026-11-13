from dataclasses import dataclass


@dataclass
class Machine:
    ui: str = "checking"
    progress: float = 0.0
    fallback: str | None = None
    retries: int = 0
    max_retries: int = 2

    def on_status(self, status: str) -> str:
        self.ui = "ready"  # TODO: every status looks ready. Users will not thank you.
        return self.ui

    def on_progress(self, fraction: float) -> str:
        self.progress = fraction
        return self.ui

    def on_error(self, code: str) -> str:
        raise NotImplementedError
