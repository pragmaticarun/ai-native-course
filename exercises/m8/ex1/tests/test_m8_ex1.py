from typing import Any

import pytest
from _impl import load

impl = load(__file__)


class PaymentsAPI:
    """Fake payment provider. Times out (after charging!) on the calls listed in `timeouts`."""

    def __init__(self, timeouts=()):
        self.timeouts = set(timeouts)
        self.calls = 0
        self.charges: list[tuple[str, int]] = []
        self.by_key: dict[str, dict] = {}

    def charge(self, account, cents, idempotency_key=None):
        self.calls += 1
        if idempotency_key is not None and idempotency_key in self.by_key:
            result = self.by_key[idempotency_key]
        else:
            self.charges.append((account, cents))
            result = {"charge_id": f"ch_{len(self.charges)}", "cents": cents}
            if idempotency_key is not None:
                self.by_key[idempotency_key] = result
        if self.calls in self.timeouts:
            raise TimeoutError("gateway timeout")  # the charge already happened
        return result


def test_timeout_after_charge_does_not_double_charge():
    api = PaymentsAPI(timeouts={1})
    out = impl.safe_charge(api, {}, "run-7", 3, "acct_1", 1999)
    assert out == {"charge_id": "ch_1", "cents": 1999}
    assert api.charges == [("acct_1", 1999)] and api.calls == 2


def test_replayed_step_is_served_from_the_store():
    api, store = PaymentsAPI(), dict[str, Any]()
    first = impl.safe_charge(api, store, "run-7", 3, "acct_1", 1999)
    again = impl.safe_charge(api, store, "run-7", 3, "acct_1", 1999)  # the workflow replays
    assert first == again and api.calls == 1


def test_different_steps_are_different_charges():
    api, store = PaymentsAPI(), dict[str, Any]()
    impl.safe_charge(api, store, "run-7", 3, "acct_1", 1999)
    impl.safe_charge(api, store, "run-7", 4, "acct_1", 1999)
    assert len(api.charges) == 2


def test_gives_up_after_attempts():
    api = PaymentsAPI(timeouts={1, 2, 3})
    with pytest.raises(TimeoutError):
        impl.safe_charge(api, {}, "r", 1, "a", 5, attempts=3)
    assert api.calls == 3 and len(api.charges) == 1


def test_key_reuse_with_other_arguments_is_a_bug():
    api, store = PaymentsAPI(), dict[str, Any]()
    impl.safe_charge(api, store, "r", 1, "a", 5)
    with pytest.raises(ValueError):
        impl.safe_charge(api, store, "r", 1, "a", 500)
