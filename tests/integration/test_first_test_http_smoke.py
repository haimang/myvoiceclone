import os

import pytest


@pytest.mark.live
def test_first_test_http_smoke_gated():
    if os.getenv("RUN_LIVE_HTTP") != "1":
        pytest.skip("RUN_LIVE_HTTP=1 is required for live HTTP first-test smoke")
