from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base for response schemas read directly from SQLAlchemy ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
