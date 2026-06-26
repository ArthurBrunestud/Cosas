from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
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
    # IDs de todos los managers para identificar lugares "corporativos"
    managers_result = await db.execute(
        select(User.id).where(User.role == "manager")
    )
    manager_ids = [row[0] for row in managers_result.all()]

    base_filters = [
        Place.active == True,
        Place.name.ilike(f"%{q}%"),
    ]

    if current_user.role == "pyme":
        # pyme ve: sus propios lugares + cualquier lugar creado por un manager
        visibility = or_(
            Place.created_by == current_user.id,
            Place.created_by.in_(manager_ids),
        )
    elif current_user.role in ("vehicular", "convenio"):
        # vehicular/convenio ve:
        # - lugares asignados a su rol (creados por manager para ese rol)
        # - sus propios lugares personales (sin role_assign)
        visibility = or_(
            (Place.role_assign == current_user.role),
            (Place.created_by == current_user.id),
        )
    else:
        # cualquier otro rol (incluido manager si por error llega aquí) no ve nada
        return []

    query = select(Place).where(*base_filters, visibility).order_by(Place.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=PlaceOut)
async def create_place(
    body: PlaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Todos los workers (pyme, vehicular, convenio) pueden crear lugares
    # personales desde la app. Solo los managers tienen prohibido este endpoint
    # (ellos usan /manager/places).
    if current_user.role not in ("pyme", "vehicular", "convenio"):
        raise HTTPException(
            status_code=403,
            detail="Este endpoint es solo para trabajadores"
        )

    place = Place(
        name=body.name,
        address=body.address,
        lat=body.lat,
        lng=body.lng,
        active=True,
        created_by=current_user.id,
        role_assign=None,  # los lugares personales no llevan role_assign
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
    # Cualquier worker puede borrar SUS propios lugares (soft-delete).
    # Nunca puede borrar lugares de otros (ni de un manager ni de otro worker).
    if current_user.role not in ("pyme", "vehicular", "convenio"):
        raise HTTPException(
            status_code=403,
            detail="Este endpoint es solo para trabajadores"
        )

    result = await db.execute(
        select(Place).where(Place.id == place_id)
    )
    place = result.scalar_one_or_none()
    if not place:
        raise HTTPException(status_code=404, detail="Lugar no encontrado")

    if place.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="No puedes eliminar un lugar que no creaste"
        )

    place.active = False
    await db.commit()