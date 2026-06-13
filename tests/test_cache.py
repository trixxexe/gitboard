import time

import pytest

from gitboard.cache import DiskCache


@pytest.fixture
def cache(tmp_path):
    db_path = tmp_path / "test_cache.db"
    c = DiskCache(db_path=db_path)
    yield c
    c.close()


def test_set_and_get(cache):
    cache.set("key1", {"hello": "world"})
    assert cache.get("key1") == {"hello": "world"}


def test_get_missing_key(cache):
    assert cache.get("nonexistent") is None


def test_expiry(cache):
    cache.set("exp", "value", ttl=0)
    time.sleep(0.01)
    assert cache.get("exp") is None


def test_overwrite(cache):
    cache.set("k", "first")
    cache.set("k", "second")
    assert cache.get("k") == "second"


def test_clear(cache):
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_persists_complex_types(cache):
    data = {
        "nested": {"list": [1, 2, 3], "bool": True, "none": None},
        "number": 42,
    }
    cache.set("complex", data)
    assert cache.get("complex") == data


def test_custom_ttl(cache):
    cache.set("ttl", "val", ttl=3600)
    assert cache.get("ttl") == "val"
