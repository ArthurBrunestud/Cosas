from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Place, PlaceCheckin, User
from app.dependencies import get_current_manager
from app.schemas import PlaceManagerOut, PlaceUpdate, PlaceVisitOut, PlaceCreate

router = APIRouter()


@router.get("/", response_model=list[PlaceManagerOut])
async def list_places(
    q: str = Query(""),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    query = select(Place).where(Place.name.ilike(f"%{q}%"))
    if active_only:
        query = query.where(Place.active == True)
    result = await db.execute(query.order_by(Place.name))
    return result.scalars().all()

@router.post("/", response_model=PlaceManagerOut)
async def create_place_manager(
    body: PlaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    if body.role_assign not in ("vehicular", "convenio"):
        raise HTTPException(
            status_code=400,
            detail="role_assign debe ser 'vehicular' o 'convenio'"
        )

    place = Place(
        name=body.name,
        address=body.address,
        lat=body.lat,
        lng=body.lng,
        active=True,
        created_by=current_user.id,
        role_assign=body.role_assign
    )
    db.add(place)
    await db.commit()
    await db.refresh(place)
    return place


@router.get("/{place_id}", response_model=PlaceManagerOut)
async def get_place(
    place_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    result = await db.execute(select(Place).where(Place.id == place_id))
    place = result.scalar_one_or_none()
    if not place:
        raise HTTPException(status_code=404, detail="Lugar no encontrado")
    return place


@router.patch("/{place_id}", response_model=PlaceManagerOut)
async def update_place(
    place_id: int,
    body: PlaceUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    result = await db.execute(select(Place).where(Place.id == place_id))
    place = result.scalar_one_or_none()
    if not place:
        raise HTTPException(status_code=404, detail="Lugar no encontrado")

    if body.name is not None:
        place.name = body.name
    if body.address is not None:
        place.address = body.address
    if body.lat is not None:
        place.lat = body.lat
    if body.lng is not None:
        place.lng = body.lng
    if body.active is not None:
        place.active = body.active

    await db.commit()
    await db.refresh(place)
    return place


@router.get("/{place_id}/visits", response_model=list[PlaceVisitOut])
async def get_place_visits(
    place_id: int,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    result = await db.execute(
        select(PlaceCheckin, User.name)
        .join(User, PlaceCheckin.user_id == User.id)
        .where(PlaceCheckin.place_id == place_id)
        .order_by(PlaceCheckin.checked_in_at.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        PlaceVisitOut(
            checkin_id=checkin.id,
            worker_id=checkin.user_id,
            worker_name=worker_name,
            session_id=checkin.session_id,
            checked_in_at=checkin.checked_in_at,
            notes=checkin.notes
        )
        for checkin, worker_name in rows
    ]

@router.delete("/{place_id}", status_code=204)
async def delete_place_manager(
    place_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    result = await db.execute(
        select(Place).where(Place.id == place_id)
    )
    place = result.scalar_one_or_none()
    if not place:
        raise HTTPException(status_code=404, detail="Lugar no encontrado")
    if place.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Solo puedes eliminar lugares que tú creaste"
        )

    place.active = False
    await db.commit()