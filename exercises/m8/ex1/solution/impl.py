from typing import Any


def safe_charge(
    api: Any,
    store: dict[str, Any],
    run_id: str,
    step: int,
    account: str,
    cents: int,
    *,
    attempts: int = 3,
) -> dict[str, Any]:
    key = f"{run_id}:{step}"
    request = {"account": account, "cents": cents}
    if key in store:
        saved = store[key]
        if saved["request"] != request:
            raise ValueError(f"idempotency key {key} reused with different arguments")
        result: dict[str, Any] = saved["result"]
        return result
    for _ in range(attempts):
        try:
            result = api.charge(account, cents, idempotency_key=key)
        except TimeoutError:
            continue
        store[key] = {"request": request, "result": result}
        return result
    raise TimeoutError(f"charge {key} timed out {attempts} times")
