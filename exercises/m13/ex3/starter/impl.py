def has_pii(text: str) -> bool:
    return "@" in text  # TODO: phones and cards too


def route(prompt: str, sensitive: bool, online: bool, local_ok: bool, local_ctx: int, est_tokens: int,  # noqa: E501
          hard: bool) -> str:  # fmt: skip
    if hard or not local_ok:
        return "cloud"  # TODO: this ships private data to the cloud
    return "local"
