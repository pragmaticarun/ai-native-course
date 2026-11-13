import pytest
from _impl import load

impl = load(__file__)

# Facts as presented in lessons L1.2-L1.5 (see their sources).
FRAMEWORKS = {
    "Gartner AI Maturity Model": (True, "organisation", False),
    "MIT CISR Enterprise AI Maturity": (True, "organisation", False),
    "Google Cloud AI Adoption Framework": (False, "organisation", True),
    "AWS CAF-AI": (False, "organisation", True),
    "DORA AI Capabilities Model": (False, "engineering_team", False),
    "Shapiro five levels": (True, "engineering_team", False),
    "Feng et al. autonomy levels": (True, "agent", False),
}
EXPECTED_KIND = {
    "Gartner AI Maturity Model": "ladder",
    "MIT CISR Enterprise AI Maturity": "ladder",
    "Google Cloud AI Adoption Framework": "map",
    "AWS CAF-AI": "map",
    "DORA AI Capabilities Model": "map",
    "Shapiro five levels": "ladder",
    "Feng et al. autonomy levels": "ladder",
}


@pytest.mark.parametrize("name", FRAMEWORKS)
def test_classification(name):
    ordered, subject, sells = FRAMEWORKS[name]
    out = impl.classify(
        {"ordered_levels": ordered, "subject": subject, "publisher_sells_platform": sells}
    )
    assert out == {"kind": EXPECTED_KIND[name], "scope": subject, "vendor_bias_check": sells}
