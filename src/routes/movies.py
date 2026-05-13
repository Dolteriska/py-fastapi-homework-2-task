from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas import MovieListItemSchema, MovieDetailSchema, MovieListResponseSchema
from schemas.movies import CustomMoviePagination, MovieCreateSchema, MovieUpdate

router = APIRouter()


@router.get("/movies/", response_model=CustomMoviePagination)
async def read_movies(
        request: Request,
        page: int = Query(1, ge=1, description="The page number to fetch"),
        per_page: int = Query(10, ge=1, le=20, description="Number of movies per page"),
        db: AsyncSession = Depends(get_db)
):
    count_query = select(func.count()).select_from(MovieModel)
    total_items = await db.scalar(count_query)

    if total_items == 0 or total_items is None:
        raise HTTPException(status_code=404, detail="No movies found.")
    total_pages = (total_items + per_page - 1) // per_page

    if page > total_pages:
        raise HTTPException(status_code=404, detail="No movies found.")
    offset = (page - 1) * per_page

    movie_query = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages)
        )
        .order_by(desc(MovieModel.id))
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(movie_query)
    movies = result.unique().scalars().all()

    base_url = "/theater/movies/"

    prev_page = (
        f"{base_url}?page={page - 1}&per_page={per_page}"
        if page > 1 else None
    )
    next_page = (
        f"{base_url}?page={page + 1}&per_page={per_page}"
        if page < total_pages else None
    )
    return {
        "movies": movies,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_pages": total_pages,
        "total_items": total_items
    }


async def get_or_create(session: AsyncSession, model, field, value):
    stmt = select(model).where(getattr(model, field) == value)
    result = await session.execute(stmt)
    instance = result.scalar_one_or_none()
    if instance:
        return instance
    instance = model(**{field: value})
    session.add(instance)
    await session.flush()
    return instance


@router.post("/movies/", response_model=MovieListItemSchema,
             status_code=201
             )
async def create_movie(movie_in: MovieCreateSchema, db: AsyncSession = Depends(get_db)):
    duplicate_stmt = select(MovieModel).where(
        MovieModel.name == movie_in.name,
        MovieModel.date == movie_in.date
    )
    duplicate_res = await db.execute(duplicate_stmt)
    if duplicate_res.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"A movie with the name '{movie_in.name}' and release date '{movie_in.date}' already exists."
        )
    country_obj = await get_or_create(db, CountryModel, "code", movie_in.country)

    genres_objs = [await get_or_create(db, GenreModel, "name", g) for g in movie_in.genres]
    actors_objs = [await get_or_create(db, ActorModel, "name", a) for a in movie_in.actors]
    languages_objs = [await get_or_create(db, LanguageModel, "name", lang) for lang in movie_in.languages]

    new_movie = MovieModel(
        name=movie_in.name,
        date=movie_in.date,
        score=movie_in.score,
        overview=movie_in.overview,
        status=movie_in.status,
        budget=movie_in.budget,
        revenue=movie_in.revenue,
        country=country_obj,
        genres=genres_objs,
        actors=actors_objs,
        languages=languages_objs
    )
    db.add(new_movie)
    try:
        await db.commit()
        stmt = select(MovieModel).options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages)
        ).where(MovieModel.id == new_movie.id)

        result = await db.execute(stmt)
        return result.unique().scalar_one()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie_by_id(movie_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages)
        )
        .where(MovieModel.id == movie_id)
    )

    result = await db.execute(stmt)
    movie = result.unique().scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )
    return movie


@router.delete("/movies/{movie_id}/", status_code=204)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    query = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    db_movie = query.unique().scalar_one_or_none()
    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")
    await db.delete(db_movie)
    await db.commit()
    return


@router.patch("/movies/{movie_id}/", status_code=200)
async def update_movie(movie: MovieUpdate, movie_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages)
        )
        .where(MovieModel.id == movie_id)
    )
    query = await db.execute(stmt)
    db_movie = query.unique().scalar_one_or_none()

    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    update_data = movie.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_movie, key, value)

    try:
        await db.commit()
        await db.refresh(db_movie)
        return {"detail": "Movie updated successfully."}
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")
