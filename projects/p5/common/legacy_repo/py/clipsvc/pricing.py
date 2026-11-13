import math

RATES = {"free": 0, "pro": 2, "studio": 5}  # cents per started minute


def price_cents(minutes: float, plan: str) -> int:
    return math.ceil(minutes) * RATES[plan]
