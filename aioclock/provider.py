from functools import lru_cache

from fast_depends import Provider


@lru_cache
def get_provider():
    """Return a Provider instance, which is singleton.
    This singleton is used to inject dependencies in tasks.
    """
    return Provider()
