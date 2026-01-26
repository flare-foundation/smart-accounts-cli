from collections.abc import Callable
from typing import Generic, TypeVar, cast

T = TypeVar("T")


class Singleton(Generic[T]):
    def __init__(self, factory: Callable[[], T]) -> None:
        self.factory = factory
        self.inner: T | None = None

    def __getattr__(self, *args, **kwargs):
        if self.inner is None:
            self.inner = self.factory()

        return getattr(self.inner, *args, **kwargs)


def wrap_singleton(factory: Callable[[], T]) -> T:
    wrapper = Singleton(factory)
    return cast(T, wrapper)
