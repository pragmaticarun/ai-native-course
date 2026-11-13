from clipsvc.pricing import price_cents
from clipsvc.tags import normalize_tags


def test_tags_are_stripped_lowercased_deduplicated():
    assert normalize_tags([" News", "news", "", "  ", "Sport"]) == ["news", "sport"]


def test_price_per_started_minute():
    assert price_cents(2.5, "pro") == 6
    assert price_cents(0, "studio") == 0
