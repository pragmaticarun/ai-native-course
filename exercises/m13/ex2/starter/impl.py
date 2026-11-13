def pareto(rows: list[dict]) -> list[dict]:
    return rows  # TODO: drop dominated rows


def pick(rows: list[dict], max_mb: float, max_kld: float) -> dict | None:
    return min(rows, key=lambda r: r["size_mb"])  # TODO: the smallest is not always the answer


def kv_cache_mb(
    n_layer: int, n_ctx: int, n_head_kv: int, head_dim: int, bytes_per_elem: float
) -> float:
    raise NotImplementedError
