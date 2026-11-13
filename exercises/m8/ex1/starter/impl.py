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
    # TODO: idempotency key, retry on TimeoutError, cache, detect key reuse with other arguments
    for _ in range(attempts):
        try:
            result: dict[str, Any] = api.charge(account, cents)
            return result
        except TimeoutError:
            continue
    raise TimeoutError("charge failed")
