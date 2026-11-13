def classify(fw: dict) -> dict:
    return {
        "kind": "ladder" if fw["ordered_levels"] else "map",
        "scope": fw["subject"],
        "vendor_bias_check": bool(fw["publisher_sells_platform"]),
    }
