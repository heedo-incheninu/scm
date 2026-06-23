from __future__ import annotations

import pytest

from scm.simulation import generate_sample_data


@pytest.fixture(scope="session")
def sample_data():
    return generate_sample_data()

