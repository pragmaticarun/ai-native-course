from dataclasses import dataclass

STATUS_UI = {
    "UNAVAILABLE": "unsupported",
    "DOWNLOADABLE": "needs_download",
    "DOWNLOADING": "downloading",
    "AVAILABLE": "ready",
}


@dataclass
class Machine:
    ui: str = "checking"
    progress: float = 0.0
    fallback: str | None = None
    retries: int = 0
    max_retries: int = 2

    def on_status(self, status: str) -> str:
        if status not in STATUS_UI:
            raise ValueError(f"unknown status {status}")
        self.ui = STATUS_UI[status]
        if status == "UNAVAILABLE":
            self.fallback = "litert_lm_cpu"
        return self.ui

    def on_progress(self, fraction: float) -> str:
        self.progress = max(self.progress, min(fraction, 1.0))
        self.ui = "ready" if self.progress >= 1.0 else "downloading"
        return self.ui

    def on_error(self, code: str) -> str:
        if code == "BACKGROUND_USE_BLOCKED":
            self.ui = "foreground_needed"
        elif code == "BUSY":
            if self.retries < self.max_retries:
                self.retries += 1
                self.ui = "retrying"
            else:
                self.ui, self.fallback = "fallback", "litert_lm_cpu"
        elif code == "PER_APP_BATTERY_USE_QUOTA_EXCEEDED":
            self.ui, self.fallback = "fallback", "litert_lm_cpu"
        else:
            raise ValueError(f"unknown error {code}")
        return self.ui
