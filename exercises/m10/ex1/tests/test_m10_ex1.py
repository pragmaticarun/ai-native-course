import re
from decimal import Decimal, InvalidOperation

import speckit
from _impl import variant_dir

SPEC = (variant_dir(__file__) / "spec.md").read_text()


def reference(text: str) -> int:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([kM]?)", text)
    if not m:
        raise ValueError(f"bad bitrate {text!r}")
    value = Decimal(m.group(1)) * {"": 1, "k": 1000, "M": 1_000_000}[m.group(2)]
    if value != value.to_integral_value():
        raise ValueError(f"not whole bits per second: {text!r}")
    return int(value)


def binary_k(text: str) -> int:
    return reference(text.replace("k", "")) * 1024 if text.endswith("k") else reference(text)


def lowercase_m(text: str) -> int:
    return reference(text.replace("m", "M"))


def allows_negative(text: str) -> int:
    return -reference(text[1:]) if text.startswith("-") else reference(text)


def truncates(text: str) -> int:
    try:
        return reference(text)
    except ValueError:
        try:
            m = re.fullmatch(r"(\d+(?:\.\d+)?)([kM])", text)
            if not m:
                raise
            return int(Decimal(m.group(1)) * {"k": 1000, "M": 1_000_000}[m.group(2)])
        except InvalidOperation:
            raise ValueError(text) from None


def examples():
    return speckit.examples_from_spec(speckit.parse_spec(SPEC))


def test_spec_lints_clean():
    assert speckit.lint_spec(speckit.parse_spec(SPEC)) == []


def test_examples_pass_on_the_reference():
    assert len(examples()) >= 6
    assert speckit.check(examples(), reference) == []


def test_every_mutant_is_caught():
    survivors = [
        m.__name__
        for m in (binary_k, lowercase_m, allows_negative, truncates)
        if not speckit.check(examples(), m)
    ]
    assert survivors == []
