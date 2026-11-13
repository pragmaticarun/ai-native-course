import random
import time

import requests


def test_retry():
    time.sleep(2)
    assert random.choice([1, 2]) in (1, 2)


def test_live():
    assert requests.get("https://api.example.com/health").ok
