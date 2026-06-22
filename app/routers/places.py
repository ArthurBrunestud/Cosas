from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Place, PlaceCheckin
from app.dependencies import get_current_user
from app.models import User
from app.schemas import PlaceCreate, PlaceOut, CheckinRequest, CheckinOut
from datetime import datetime, timezone

router = APIRouter()

@router.get("/", response_model=list[PlaceOut])
async def search_places(
    q: str = Query(""),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Place).where(Place.name.ilike(f"%{q}%"), Place.active == True)
    )
    return result.scalars().all()

@router.post("/", response_model=PlaceOut)
async def create_place(
    body: PlaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    place = Place(**body.model_dump(), created_by=current_user.id)
    db.add(place)
    await db.commit()
    await db.refresh(place)
    return place

@router.post("/checkin", response_model=CheckinOut)
async def checkin(
    body: CheckinRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    checkin = PlaceCheckin(
        session_id=body.session_id,
        place_id=body.place_id,
        user_id=current_user.id,
        lat=body.lat,
        lng=body.lng,
        accuracy_m=body.accuracy_m,
        notes=body.notes,
        checked_in_at=datetime.now(timezone.utc)
    )
    db.add(checkin)
    await db.commit()
    await db.refresh(checkin)
    return checkin


@router.delete("/{place_id}", status_code=204)
async def delete_place(
    place_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Place).where(Place.id == place_id)
    )
    place = result.scalar_one_or_none()
    if not place:
        raise HTTPException(status_code=404, detail="Lugar no encontrado")
    if place.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes eliminar un lugar que no creaste")

    place.active = False
    await db.commit()
