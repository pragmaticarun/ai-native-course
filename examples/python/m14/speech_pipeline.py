"""M14 L14.4: VAD -> ASR -> diarization -> LLM post-processing, with a latency budget.

What is real here: audio is decoded by ffmpeg to 16 kHz mono PCM, and `energy_vad` finds
voiced regions with numpy (an energy gate, *not* silero-vad). `toy_diarize` clusters
segments by dominant frequency, which only works because the fixture "speakers" are pure
tones; real diarization (pyannote.audio) uses speaker embeddings. ASR and the LLM
post-processor are fakes with the same shapes as faster-whisper/whisper.cpp output.

silero-vad, faster-whisper, whisper.cpp and pyannote.audio were **not** run (untested).
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "m6"))
from media_eval import wer  # noqa: E402

RATE = 16000


def decode_pcm(path: Path, rate: int = RATE) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate),
         "-f", "s16le", "-"],
        capture_output=True, check=True, timeout=60,
    ).stdout  # fmt: skip
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


@dataclass(frozen=True)
class Region:
    start: float
    end: float


def energy_vad(
    pcm: np.ndarray, rate: int = RATE, frame_ms: int = 30, thresh_db: float = -40.0,
    min_speech_s: float = 0.25, hangover_frames: int = 5,
) -> list[Region]:  # fmt: skip
    """Frame RMS in dBFS above `thresh_db`, with hangover so short dips don't split words."""
    n = rate * frame_ms // 1000
    frames = pcm[: len(pcm) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((frames**2).mean(axis=1)) + 1e-9)
    voiced = db > thresh_db
    out, start, quiet = [], None, 0
    for i, v in enumerate(voiced):
        if v:
            start = i if start is None else start
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet > hangover_frames:
                out.append(Region(start * n / rate, (i - quiet + 1) * n / rate))
                start, quiet = None, 0
    if start is not None:
        out.append(Region(start * n / rate, (len(voiced) - quiet) * n / rate))
    return [
        Region(round(r.start, 2), round(r.end, 2)) for r in out if r.end - r.start >= min_speech_s
    ]


def dominant_hz(pcm: np.ndarray, r: Region, rate: int = RATE) -> float:
    seg = pcm[int(r.start * rate) : int(r.end * rate)]
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    return float(np.fft.rfftfreq(len(seg), 1 / rate)[spec.argmax()])


def toy_diarize(pcm: np.ndarray, regions: Sequence[Region], tol_hz: float = 40.0) -> list[str]:
    """Label regions SPEAKER_00, SPEAKER_01... by dominant frequency (toy, see module doc)."""
    centers: list[float] = []
    labels = []
    for r in regions:
        f = dominant_hz(pcm, r)
        idx = next((i for i, c in enumerate(centers) if abs(c - f) < tol_hz), None)
        if idx is None:
            centers.append(f)
            idx = len(centers) - 1
        labels.append(f"SPEAKER_{idx:02d}")
    return labels


@dataclass(frozen=True)
class Utterance:
    speaker: str
    start: float
    end: float
    text: str


Asr = Callable[[np.ndarray, Region], str]


def scripted_asr(script: Sequence[str]) -> Asr:
    """Fake ASR: returns the next scripted line per region (same role as faster-whisper)."""
    it = iter(script)
    return lambda pcm, r: next(it, "")


def transcribe(path: Path, asr: Asr) -> list[Utterance]:
    pcm = decode_pcm(path)
    regions = energy_vad(pcm)
    speakers = toy_diarize(pcm, regions)
    return [
        Utterance(s, r.start, r.end, asr(pcm, r)) for r, s in zip(regions, speakers, strict=True)
    ]


def post_process(utts: Sequence[Utterance], fix: Callable[[str], str]) -> list[Utterance]:
    """LLM post-processing step (punctuation, names); `fix` is the mock model."""
    return [Utterance(u.speaker, u.start, u.end, fix(u.text)) for u in utts]


# ---------- latency budgets ----------


def batch_latency(audio_s: float, rtf: float, overhead_s: float = 0.0) -> float:
    """Batch: wait for the whole recording, then process it. rtf = compute s per audio s."""
    return audio_s + audio_s * rtf + overhead_s


def streaming_first_text(chunk_s: float, rtf: float, overhead_s: float = 0.0) -> float:
    """Streaming: first text after one chunk arrives and is processed."""
    return chunk_s + chunk_s * rtf + overhead_s


def streaming_keeps_up(rtf: float) -> bool:
    """A stream only keeps up if compute per audio second is < 1 (else the backlog grows)."""
    return rtf < 1.0


def corpus_wer(refs: Sequence[str], hyps: Sequence[str]) -> float:
    """Word-weighted WER over a corpus (not the mean of per-utterance WERs)."""
    words = sum(len(r.split()) for r in refs)
    return sum(wer(r, h) * len(r.split()) for r, h in zip(refs, hyps, strict=True)) / max(words, 1)
