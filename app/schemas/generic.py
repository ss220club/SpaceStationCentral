from typing import Generic, TypeVar
from pydantic import BaseModel
from starlette.datastructures import URL

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    next_page: str | None = None
    previous_page: str | None = None

    def calculate_adjacent_pages(self, current_url: URL):
        if (self.page * self.page_size) < self.total:
            self.next_page = str(
                current_url.include_query_params(
                    page=self.page+1, page_size=self.page_size)
            )
        if self.page > 1:
            self.previous_page = str(current_url.include_query_params(
                page=self.page-1, page_size=self.page_size
            ))

    def __init__(self, *args, current_url: URL | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.calculate_adjacent_pages(current_url)
