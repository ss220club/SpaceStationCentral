from typing import TYPE_CHECKING, Any, Generic, TypeVar

from app.deps import SessionDep
from fastapi import Request
from pydantic import BaseModel
from sqlmodel import func, select
from sqlmodel.sql.expression import Select


if TYPE_CHECKING:
    from fastapi.datastructures import URL


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    next_page: int | None = None
    previous_page: int | None = None
    next_page_path: str | None = None
    previous_page_path: str | None = None

    def __init__(self, **data: Any) -> None:  # noqa: ANN401
        super().__init__(**data)
        url: URL | None = data.get("current_url")

        if (self.page * self.page_size) < self.total:
            self.next_page = self.page + 1
            self.next_page_path = url.include_query_params(page=self.next_page).path if url else None
        if self.page > 1:
            self.previous_page = self.page - 1
            self.previous_page_path = url.include_query_params(page=self.previous_page).path if url else None


def paginate_selection(
    session: SessionDep, selection: Select[T], request: Request, page: int, page_size: int
) -> PaginatedResponse[T]:
    total: int = session.exec(select(func.count()).select_from(selection.subquery())).one()
    selection = selection.offset((page - 1) * page_size).limit(page_size)
    items: Any = session.exec(selection).all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        current_url=request.url,
    )
