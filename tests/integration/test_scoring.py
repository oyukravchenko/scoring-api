import hashlib
import os
from unittest.mock import Mock
import pytest

from scoring.scoring import get_interests, get_score
from scoring.store import Storage, StorageError


@pytest.fixture
def storage():
    storage = Storage(host=os.getenv('STORAGE_HOST'), port=os.getenv('STORAGE_PORT'))
    yield storage
    storage.clear()

@pytest.fixture
def broken_storage():
    storage = Mock(Storage)
    storage.cache_get.side_effect = StorageError("cache_get", "Storage failure")
    storage.get.side_effect = StorageError("get", "Storage failure")

    return storage
    

def test_get_score_with_data_from_cache(storage):
    phone = "79123456789"
    key_parts = [phone]
    cache_key = "uid:" + hashlib.md5("".join(key_parts).encode("utf-8")).hexdigest()
    storage.put(cache_key, 100500)

    score = get_score(storage, phone=phone, email="test@my.com")

    assert score == 100500


def test_get_score_with_no_data_in_cache(storage):
    phone = "79123456789"
    key_parts = [phone]
    cache_key = "uid:" + hashlib.md5("".join(key_parts).encode("utf-8")).hexdigest()
    score_in_cache = storage.get(cache_key)

    assert score_in_cache == None

    score = get_score(storage, phone=phone, email="some@test.email")

    assert score == 3.0
    assert float(storage.get(cache_key)) == 3.0


def test_get_score_with_broken_storage(broken_storage):
    score = get_score(broken_storage, phone="79123456789", email="some@test.email")

    assert score == 3.0


def test_get_interests_with_broken_storage(broken_storage):
    with pytest.raises(StorageError):
        get_interests(broken_storage, cid=1)
