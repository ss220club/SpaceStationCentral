from typing import Generic, TypeVar

from fastapi import Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel.sql.expression import SelectOfScalar
from starlette.datastructures import URL

from app.deps import SessionDep

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
                    page=self.page+1)
            )
        if self.page > 1:
            self.previous_page = str(current_url.include_query_params(
                page=self.page-1
            ))

    def __init__(self, *args, current_url: URL, **kwargs):
        super().__init__(*args, **kwargs)
        self.calculate_adjacent_pages(current_url)


def paginate_selection(session: SessionDep,
                       selection: SelectOfScalar[T],
                       request: Request,
                       page: int,
                       page_size: int) -> PaginatedResponse[T]:
    # type: ignore # pylint: disable=not-callable
    total = session.exec(selection.with_only_columns(func.count())).first()
    selection = selection.offset((page-1)*page_size).limit(page_size)
    items = session.exec(selection).all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        current_url=request.url,
    )
