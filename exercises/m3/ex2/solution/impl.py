def find_cycle(calls: list[str], min_repeats: int = 3) -> list[str] | None:
    for size in (1, 2, 3):
        need = size * min_repeats
        if len(calls) < need:
            continue
        tail = calls[-need:]
        block = tail[:size]
        if all(tail[i : i + size] == block for i in range(0, need, size)):
            return block
    return None


def should_stop(calls: list[str]) -> bool:
    return find_cycle(calls) is not None
