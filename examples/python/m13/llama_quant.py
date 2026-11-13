"""M13 L13.6 / Ex2: quantize a small GGUF model with llama.cpp and chart quality vs speed vs size.

Real tools, run on the box and in the CI `llamacpp` job:
* llama.cpp release **b12359** (the build the `v1.0.0` tag points at; its binaries report
  `version: 1.0.0-dev (build 12359)`), prebuilt `llama-b12359-bin-ubuntu-x64.tar.gz`;
* model: `ggml-org/models` `tinyllamas/stories15M.gguf` (F32, ~98 MB, a 15M-parameter
  TinyStories Llama). Tiny on purpose: the *method* transfers, the numbers don't.

Steps: `llama-quantize` F32 -> Q8_0 / Q4_K_M / Q4_0; `llama-perplexity` on
fixtures/tiny_stories_eval.txt (our own text) with `--kl-divergence` against the F32 logits;
`llama-bench -o json` for prompt and generation tokens/s. Numbers are x86 CPU numbers, **not**
Galaxy A73 numbers (the A73 run is untested).

    LLAMA_CPP_DIR=/path/to/llama-b12359 LLAMA_MODEL=/path/to/stories15M.gguf \
        uv run --project ../../python python -m m13.llama_quant
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL_TEXT = HERE / "fixtures" / "tiny_stories_eval.txt"
QUANTS = ("Q8_0", "Q4_K_M", "Q4_0")


@dataclass(frozen=True)
class Row:
    quant: str
    size_mb: float
    ppl: float
    ppl_ratio: float
    mean_kld: float
    same_top_pct: float
    pp_tps: float
    tg_tps: float


def tools() -> tuple[Path, Path] | None:
    d, m = os.environ.get("LLAMA_CPP_DIR"), os.environ.get("LLAMA_MODEL")
    if d and m and (Path(d) / "llama-quantize").exists() and Path(m).exists():
        return Path(d), Path(m)
    return None


def _run(
    bin_dir: Path, exe: str, *args: str, timeout: float = 600, stdout_only: bool = False
) -> str:
    env = {**os.environ, "LD_LIBRARY_PATH": str(bin_dir)}
    proc = subprocess.run(
        [str(bin_dir / exe), *args], capture_output=True, text=True, env=env, timeout=timeout
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{exe} failed: {proc.stderr[-400:]}")
    return proc.stdout if stdout_only else proc.stdout + proc.stderr


def parse_kld(text: str) -> dict[str, float]:
    """Pull the summary numbers out of `llama-perplexity --kl-divergence` output."""

    def num(pattern: str) -> float:
        m = re.search(pattern, text)
        if not m:
            raise ValueError(f"not found: {pattern}")
        return float(m.group(1))

    return {
        "ppl": num(r"Mean PPL\(Q\)\s*:\s*([\d.]+)"),
        "ppl_base": num(r"Mean PPL\(base\)\s*:\s*([\d.]+)"),
        "ppl_ratio": num(r"Mean PPL\(Q\)/PPL\(base\)\s*:\s*([\d.]+)"),
        "mean_kld": num(r"Mean\s+KLD:\s*([\d.]+)"),
        "same_top_pct": num(r"Same top p:\s*([\d.]+)"),
    }


def parse_bench(js: str) -> dict[str, tuple[float, float]]:
    """llama-bench -o json -> {model_filename: (prompt t/s, generation t/s)}."""
    out: dict[str, list[float]] = {}
    for r in json.loads(js):
        key = Path(r["model_filename"]).name
        out.setdefault(key, [0.0, 0.0])[0 if r["n_prompt"] else 1] = float(r["avg_ts"])
    return {k: (v[0], v[1]) for k, v in out.items()}


def kv_cache_bytes(
    n_layer: int, n_ctx: int, n_head_kv: int, head_dim: int, bytes_per_elem: float
) -> int:
    """K and V, every layer, every position. Weight quantization does not change this; the
    KV cache *type* (`-ctk/-ctv`), fewer KV heads (GQA/MQA) or a shorter context do."""
    return int(2 * n_layer * n_ctx * n_head_kv * head_dim * bytes_per_elem)


def run(bin_dir: Path, model: Path, work: Path, threads: int = 4, ctx: int = 128) -> list[Row]:
    base = work / "base.kld"
    _run(bin_dir, "llama-perplexity", "-m", str(model), "-f", str(EVAL_TEXT), "-c", str(ctx), "-t", str(threads),  # noqa: E501
         "--kl-divergence-base", str(base))  # fmt: skip
    files = {"F32": model}
    for q in QUANTS:
        files[q] = work / f"model-{q.lower()}.gguf"
        _run(bin_dir, "llama-quantize", str(model), str(files[q]), q)
    bench_args = [a for f in files.values() for a in ("-m", str(f))]
    bench = parse_bench(_run(bin_dir, "llama-bench", *bench_args, "-p", "64", "-n", "32", "-t", str(threads),  # noqa: E501
                             "-r", "3", "-o", "json", stdout_only=True))  # fmt: skip
    rows = []
    for q, f in files.items():
        if q == "F32":
            k = {"ppl": float("nan"), "ppl_ratio": 1.0, "mean_kld": 0.0, "same_top_pct": 100.0}
            k["ppl"] = float(re.search(r"PPL = ([\d.]+)", _run(bin_dir, "llama-perplexity", "-m", str(f), "-f",  # noqa: E501
                             str(EVAL_TEXT), "-c", str(ctx), "-t", str(threads)))[1])  # type: ignore[index]  # fmt: skip
        else:
            k = parse_kld(_run(bin_dir, "llama-perplexity", "-m", str(f), "-c", str(ctx), "-t", str(threads),  # noqa: E501
                               "--kl-divergence-base", str(base), "--kl-divergence"))  # fmt: skip
        pp, tg = bench[f.name]
        rows.append(Row(q, round(f.stat().st_size / 1e6, 1), round(k["ppl"], 3), round(k["ppl_ratio"], 4),  # noqa: E501
                        round(k["mean_kld"], 4), round(k["same_top_pct"], 1), round(pp, 1), round(tg, 1)))  # fmt: skip  # noqa: E501
    return rows


def table(rows: list[Row]) -> str:
    head = "| quant | size MB | PPL | PPL/F32 | mean KLD | same top-1 % | prompt t/s | gen t/s |\n|---|---|---|---|---|---|---|---|"  # noqa: E501
    body = "\n".join(
        f"| {r.quant} | {r.size_mb} | {r.ppl} | {r.ppl_ratio} | {r.mean_kld} | {r.same_top_pct} | {r.pp_tps} | {r.tg_tps} |"  # noqa: E501
        for r in rows
    )
    return f"{head}\n{body}"


if __name__ == "__main__":
    t = tools()
    if t is None:
        raise SystemExit("set LLAMA_CPP_DIR and LLAMA_MODEL (see module docstring)")
    with tempfile.TemporaryDirectory() as tmp:
        print(table(run(*t, Path(tmp))))
