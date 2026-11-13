from dataclasses import dataclass, field


def pipeline(model_file: str, out_file: str) -> str:
    return (
        "videotestsrc num-buffers=300 ! videoconvert ! "
        f"onnxinference model-file={model_file} ! tensordecodebin ! fakesink"
    )


@dataclass
class Recorder:
    on: float = 0.6
    off: float = 0.4
    start_frames: int = 3
    stop_s: float = 2.0
    recording: bool = False
    segments: list[tuple[float, float]] = field(default_factory=list)
    _hits: int = 0
    _quiet_since: float | None = None
    _start_t: float = 0.0

    def on_frame(self, t: float, person_score: float) -> str | None:
        if not self.recording:
            self._hits = self._hits + 1 if person_score >= self.on else 0
            if self._hits >= self.start_frames:
                self.recording, self._start_t, self._quiet_since = True, t, None
                return "start"
            return None
        if person_score < self.off:
            self._quiet_since = t if self._quiet_since is None else self._quiet_since
            if t - self._quiet_since >= self.stop_s - 1e-9:  # float timestamps
                self.recording, self._hits = False, 0
                self.segments.append((self._start_t, t))
                return "stop"
        else:
            self._quiet_since = None
        return None
