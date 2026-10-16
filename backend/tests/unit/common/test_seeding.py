import uuid

import pytest

from houseplants.common.seeding import seed_id


def test_seed_id_reads_as_its_kind_and_number():
    assert seed_id(2, 1) == uuid.UUID("00000002-0000-4000-8000-000000000001")
    assert seed_id(5, 10203) == uuid.UUID("00000005-0000-4000-8000-000000010203")


def test_seed_id_is_a_valid_version_4_uuid():
    assert seed_id(1, 1).version == 4


@pytest.mark.parametrize("kind, number", [(0, 1), (1, 0), (10**8, 1), (1, 10**12)])
def test_seed_id_rejects_out_of_range_parts(kind, number):
    with pytest.raises(ValueError):
        seed_id(kind, number)
