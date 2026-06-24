from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.database import get_db
from app.models import Place, PlaceCheckin, User
from app.dependencies import get_current_user
from app.schemas import PlaceCreate, PlaceOut, CheckinRequest, CheckinOut

router = APIRouter()


@router.get("/", response_model=list[PlaceOut])
async def list_places(
    q: str = Query(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "pyme":
        query = select(Place).where(
            Place.active == True,
            Place.created_by == current_user.id,
            Place.name.ilike(f"%{q}%")
        )
    else:
        query = select(Place).where(
            Place.active == True,
            Place.role_assign == current_user.role,
            Place.name.ilike(f"%{q}%")
        )
    result = await db.execute(query.order_by(Place.name))
    return result.scalars().all()


@router.post("/", response_model=PlaceOut)
async def create_place(
    body: PlaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "pyme":
        raise HTTPException(
            status_code=403,
            detail="Solo los workers pyme pueden crear lugares desde la app"
        )
    place = Place(
        name=body.name,
        address=body.address,
        lat=body.lat,
        lng=body.lng,
        active=True,
        created_by=current_user.id,
        role_assign=None
    )
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
    if current_user.role != "pyme":
        raise HTTPException(
            status_code=403,
            detail="Solo los workers pyme pueden eliminar lugares desde la app"
        )
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