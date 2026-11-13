NOTIFICATION = "Your parcel is on its way."  # TODO: write an actual injection attempt


def normalise(text: str) -> str:
    return text.lower()


def scan(text: str) -> list[str]:
    return ["override"] if "ignore previous instructions" in text.lower() else []


def allow(action: str, target: str, screen_text: str) -> bool:
    return True
