from functools import lru_cache

from fast_depends import Provider


@lru_cache
def get_provider():
    return Provider()
