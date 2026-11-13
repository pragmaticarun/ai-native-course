"""M13 L13.6: the host half of the ORT stretch: a small ONNX classifier, quantized, measured.

Real: numpy trains a 2-layer MLP on a synthetic 3-class problem, `onnx.helper` writes it as an
ONNX graph, ONNX Runtime (CPU EP) runs it, and `onnxruntime.quantization.quantize_dynamic`
makes an int8-weight copy. We report file size, accuracy, agreement with FP32 and latency.

Not run: the ORT **QNN** execution provider on the Galaxy A73's Hexagon HTP (the syllabus
"may not work" stretch). That needs the device and Qualcomm's QNN SDK (untested).
"""

from __future__ import annotations

import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
from onnx import TensorProto, helper, numpy_helper
from onnxruntime.quantization import QuantType, quantize_dynamic


def make_data(n: int, seed: int = 0, dim: int = 64) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    centers = np.random.default_rng(42).normal(0, 1.0, (3, dim))  # same classes for every split
    y = rng.integers(0, 3, n)
    x = centers[y] + rng.normal(0, 1.6, (n, dim))
    return x.astype(np.float32), y


def train_mlp(
    x: np.ndarray,
    y: np.ndarray,
    hidden: int = 256,
    epochs: int = 150,
    lr: float = 0.1,
    seed: int = 0,
):
    rng = np.random.default_rng(seed)
    w1 = rng.normal(0, 0.1, (x.shape[1], hidden)).astype(np.float32)
    b1 = np.zeros(hidden, np.float32)
    w2 = rng.normal(0, 0.1, (hidden, 3)).astype(np.float32)
    b2 = np.zeros(3, np.float32)
    onehot = np.eye(3, dtype=np.float32)[y]
    for _ in range(epochs):
        h = np.maximum(x @ w1 + b1, 0)
        logits = h @ w2 + b2
        p = np.exp(logits - logits.max(1, keepdims=True))
        p /= p.sum(1, keepdims=True)
        g = (p - onehot) / len(x)
        gw2, gb2 = h.T @ g, g.sum(0)
        gh = (g @ w2.T) * (h > 0)
        gw1, gb1 = x.T @ gh, gh.sum(0)
        w1 -= lr * gw1
        b1 -= lr * gb1
        w2 -= lr * gw2
        b2 -= lr * gb2
    return w1, b1, w2, b2


def to_onnx(weights, path: Path) -> Path:
    w1, b1, w2, b2 = weights
    inits = [
        numpy_helper.from_array(a, n)
        for a, n in zip(weights, ["w1", "b1", "w2", "b2"], strict=True)
    ]
    nodes = [
        helper.make_node("MatMul", ["x", "w1"], ["h0"]),
        helper.make_node("Add", ["h0", "b1"], ["h1"]),
        helper.make_node("Relu", ["h1"], ["h"]),
        helper.make_node("MatMul", ["h", "w2"], ["l0"]),
        helper.make_node("Add", ["l0", "b2"], ["logits"]),
    ]
    graph = helper.make_graph(
        nodes, "mlp",
        [helper.make_tensor_value_info("x", TensorProto.FLOAT, ["N", w1.shape[0]])],
        [helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["N", 3])],
        inits,
    )  # fmt: skip
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 10
    onnx.checker.check_model(model)
    onnx.save(model, path)
    return path


@dataclass(frozen=True)
class Result:
    name: str
    size_kb: float
    accuracy: float
    agreement: float
    ms_per_batch: float


def evaluate(
    path: Path, x: np.ndarray, y: np.ndarray, ref: np.ndarray | None, reps: int = 50
) -> tuple[Result, np.ndarray]:
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    pred = sess.run(None, {"x": x})[0].argmax(1)
    t0 = time.perf_counter()
    for _ in range(reps):
        sess.run(None, {"x": x})
    ms = (time.perf_counter() - t0) / reps * 1000
    agree = 1.0 if ref is None else float((pred == ref).mean())
    return Result(
        path.stem,
        round(path.stat().st_size / 1024, 1),
        float((pred == y).mean()),
        agree,
        round(ms, 3),
    ), pred


def run(work: Path) -> list[Result]:
    xtr, ytr = make_data(3000, seed=1)
    xte, yte = make_data(1000, seed=2)
    fp32 = to_onnx(train_mlp(xtr, ytr), work / "fp32.onnx")
    int8 = work / "int8.onnx"
    quantize_dynamic(str(fp32), str(int8), weight_type=QuantType.QInt8)
    r32, ref = evaluate(fp32, xte, yte, None)
    r8, _ = evaluate(int8, xte, yte, ref)
    return [r32, r8]


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        for r in run(Path(tmp)):
            print(r)
