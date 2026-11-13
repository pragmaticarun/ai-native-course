"""M13 L13.2 / Ex1: a feature-availability state machine with honest UX.

Modelled on ML Kit GenAI's documented flow: check a feature's status (UNAVAILABLE,
DOWNLOADABLE, DOWNLOADING, AVAILABLE), download if needed, then run, handling documented
runtime errors (BACKGROUND_USE_BLOCKED, BUSY, PER_APP_BATTERY_USE_QUOTA_EXCEEDED).
Python mirror of the KMP `commonMain` version (kmp/shared/.../m13/Availability.kt).

`A73_EXPECTED` encodes what the docs say a Galaxy A73 should answer (Gemini Nano features:
unsupported; speech recognition Basic mode: available on API 31+). It is **not captured from
the device (untested)**.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FeatureStatus(Enum):
    UNAVAILABLE = "UNAVAILABLE"
    DOWNLOADABLE = "DOWNLOADABLE"
    DOWNLOADING = "DOWNLOADING"
    AVAILABLE = "AVAILABLE"


class Ui(Enum):
    CHECKING = "Checking what this phone supports..."
    UNSUPPORTED = "Not available on this phone. Using the fallback."
    NEEDS_DOWNLOAD = "Download the on-device model?"
    DOWNLOADING = "Downloading model..."
    READY = "Ready"
    RUNNING = "Working..."
    RETRY_IN_FOREGROUND = "Open the app to continue (on-device AI only runs in the foreground)."
    BUSY_RETRY = "The on-device model is busy. Retrying..."
    QUOTA = "On-device limit reached for now. Using the fallback."


@dataclass
class Machine:
    feature: str
    ui: Ui = Ui.CHECKING
    progress: float = 0.0
    fallback: str | None = None
    retries: int = 0
    max_retries: int = 2

    def on_status(self, s: FeatureStatus) -> Ui:
        if s is FeatureStatus.UNAVAILABLE:
            self.ui, self.fallback = Ui.UNSUPPORTED, "cloud_or_litert_lm"
        elif s is FeatureStatus.DOWNLOADABLE:
            self.ui = Ui.NEEDS_DOWNLOAD
        elif s is FeatureStatus.DOWNLOADING:
            self.ui = Ui.DOWNLOADING
        else:
            self.ui = Ui.READY
        return self.ui

    def on_download_progress(self, fraction: float) -> Ui:
        self.progress = max(self.progress, min(fraction, 1.0))  # never goes backwards on screen
        self.ui = Ui.READY if self.progress >= 1.0 else Ui.DOWNLOADING
        return self.ui

    def on_run(self) -> Ui:
        if self.ui is not Ui.READY:
            raise RuntimeError(f"cannot run from {self.ui.name}")
        self.ui = Ui.RUNNING
        return self.ui

    def on_error(self, code: str) -> Ui:
        if code == "BACKGROUND_USE_BLOCKED":
            self.ui = Ui.RETRY_IN_FOREGROUND
        elif code == "BUSY" and self.retries < self.max_retries:
            self.retries += 1
            self.ui = Ui.BUSY_RETRY
        elif code in ("BUSY", "PER_APP_BATTERY_USE_QUOTA_EXCEEDED"):
            self.ui, self.fallback = Ui.QUOTA, "cloud_or_litert_lm"
        else:
            raise ValueError(f"unknown error code {code}")
        return self.ui

    def on_result(self) -> Ui:
        self.ui, self.retries = Ui.READY, 0
        return self.ui


A73_EXPECTED = {
    "genai-prompt (Gemini Nano)": FeatureStatus.UNAVAILABLE,
    "genai-summarization (Gemini Nano)": FeatureStatus.UNAVAILABLE,
    "speech-recognition Basic": FeatureStatus.AVAILABLE,
    "speech-recognition Advanced": FeatureStatus.UNAVAILABLE,
}
