from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Standard shape for a filtered, paged list."""

    items: list[T]
    total: int
    page: int
    page_size: int


def paginate(query, page: int, page_size: int):
    """Count first, then fetch just the requested slice."""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total, page, page_size
