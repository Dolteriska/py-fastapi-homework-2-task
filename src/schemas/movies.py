import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator

from database.models import MovieStatusEnum


class CountryBase(BaseModel):
    code: str
    name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CountryResponse(CountryBase):
    id: int

class GenreBase(BaseModel):
    name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GenreResponse(GenreBase):
    id: int


class ActorBase(BaseModel):
    name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ActorResponse(ActorBase):
    id: int


class LanguageBase(BaseModel):
    name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LanguageResponse(LanguageBase):
    id: int


class MovieBase(BaseModel):
    name: str = Field(..., max_length=255)
    date: datetime.date
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: MovieStatusEnum
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)


class MovieCreateSchema(MovieBase):
    country: str = Field(..., description="ISO 3166-1 alpha-3 code")
    genres: list[str]
    actors: list[str]
    languages: list[str]

    @field_validator("date")
    @classmethod
    def date_not_too_far(cls, v: datetime.date) -> datetime.date:
        max_date = datetime.date.today() + datetime.timedelta(days=365)
        if v > max_date:
            raise ValueError('The date must not be more than one year in the future.')
        return v


class MovieUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    date: Optional[datetime.date] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    overview: Optional[str] = None
    status: Optional[MovieStatusEnum] = None
    budget: Optional[float] = Field(None, ge=0)
    revenue: Optional[float] = Field(None, ge=0)

    @field_validator("date")
    @classmethod
    def date_not_too_far(cls, v: datetime.date) -> datetime.date:
        max_date = datetime.date.today() + datetime.timedelta(days=365)
        if v > max_date:
            raise ValueError('The date must not be more than one year in the future.')
        return v


class MovieListResponseSchema(BaseModel):
    id: int
    name: str
    date: datetime.date
    score: float
    overview: str
    model_config = ConfigDict(from_attributes=True)


class MovieListItemSchema(MovieBase):
    id: int
    country: CountryResponse
    genres: list[GenreResponse]
    actors: list[ActorResponse]
    languages: list[LanguageResponse]
    model_config = ConfigDict(from_attributes=True)


class CustomMoviePagination(BaseModel):
    movies: List[MovieListResponseSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


class MovieDetailSchema(MovieBase):
    id: int
    country: CountryResponse
    genres: list[GenreResponse]
    actors: list[ActorResponse]
    languages: list[LanguageResponse]
