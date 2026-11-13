import re

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_PHONE = re.compile(r"(?<![\d])\+?\d(?:[ -]?\d){9,}(?![\d])")
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def has_pii(text: str) -> bool:
    return any(rx.search(text) for rx in (_EMAIL, _PHONE, _CARD))


def route(prompt: str, sensitive: bool, online: bool, local_ok: bool, local_ctx: int, est_tokens: int,  # noqa: E501
          hard: bool) -> str:  # fmt: skip
    fits = local_ok and est_tokens <= local_ctx
    if sensitive or has_pii(prompt):
        return "local" if fits else "refuse"
    if not online:
        return "local" if fits else "refuse"
    if not fits or hard:
        return "cloud"
    return "local"
