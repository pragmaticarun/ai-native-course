from dataclasses import dataclass, field


def pipeline(model_file: str, out_file: str) -> str:
    return f"v4l2src ! videoconvert ! onnxinference model-file={model_file} ! autovideosink"


@dataclass
class Recorder:
    on: float = 0.6
    off: float = 0.4
    start_frames: int = 3
    stop_s: float = 2.0
    recording: bool = False
    segments: list[tuple[float, float]] = field(default_factory=list)

    def on_frame(self, t: float, person_score: float) -> str | None:
        # TODO: one frame above 0.5 starts, one below stops: it will flap
        if person_score > 0.5 and not self.recording:
            self.recording = True
            return "start"
        if person_score <= 0.5 and self.recording:
            self.recording = False
            return "stop"
        return None
