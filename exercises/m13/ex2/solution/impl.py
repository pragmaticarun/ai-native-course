def _dominates(a: dict, b: dict) -> bool:
    no_worse = (
        a["size_mb"] <= b["size_mb"]
        and a["mean_kld"] <= b["mean_kld"]
        and a["tg_tps"] >= b["tg_tps"]
    )
    better = (
        a["size_mb"] < b["size_mb"] or a["mean_kld"] < b["mean_kld"] or a["tg_tps"] > b["tg_tps"]
    )
    return no_worse and better


def pareto(rows: list[dict]) -> list[dict]:
    return [r for r in rows if not any(_dominates(o, r) for o in rows if o is not r)]


def pick(rows: list[dict], max_mb: float, max_kld: float) -> dict | None:
    ok = [r for r in rows if r["size_mb"] <= max_mb and r["mean_kld"] <= max_kld]
    return max(ok, key=lambda r: r["tg_tps"]) if ok else None


def kv_cache_mb(
    n_layer: int, n_ctx: int, n_head_kv: int, head_dim: int, bytes_per_elem: float
) -> float:
    return 2 * n_layer * n_ctx * n_head_kv * head_dim * bytes_per_elem / 1e6
