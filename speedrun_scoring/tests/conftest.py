import pytest

from speedrun_scoring import generate_fixture

STAMP = "2026-07-01T00:00:00Z"


@pytest.fixture
def fixture():
    return generate_fixture(seed=7)


@pytest.fixture
def at_ts(fixture):
    return max(r.ts for r in fixture.reviews) + 1.0
