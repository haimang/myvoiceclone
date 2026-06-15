import pytest

from myvoiceclone.ids import is_mvc_id, new_id


@pytest.mark.unit
def test_new_id_uses_mvc_uuid_contract():
    value = new_id()

    assert is_mvc_id(value)
    assert len(value) == 36
    assert not is_mvc_id("run_123")
    assert not is_mvc_id("mvc_not-a-uuid")
