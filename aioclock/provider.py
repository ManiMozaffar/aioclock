from __future__ import annotations

import sys
from functools import lru_cache
from inspect import signature
from typing import Any, Callable, TypeVar

from fast_depends import Provider, inject

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec


P = ParamSpec("P")
T = TypeVar("T")


@lru_cache
def get_provider() -> Provider:
    """Return a Provider instance, which is singleton.
    This singleton is used to inject dependencies in tasks.
    """
    return Provider()


def inject_with_provider(func: Callable[P, T]) -> Callable[P, T]:
    """Inject dependencies using AioClock's provider across FastDepends different versions."""

    # v2 -> dependency_overrides_provider
    # v3 -> dependency_provider
    # commit: 4beac5f4c1959f53a6bf98e42375da4b24e4ac92

    provider_keyword = (
        "dependency_provider"
        if "dependency_provider" in signature(inject).parameters
        else "dependency_overrides_provider"
    )
    inject_kwargs: dict[str, Any] = {provider_keyword: get_provider()}
    return inject(func, **inject_kwargs)
