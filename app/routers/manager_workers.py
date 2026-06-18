from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from app.database import get_db
from app.models import User
from app.dependencies import get_current_manager
from app.schemas import WorkerCreate, WorkerOut, WorkerUpdate

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/", response_model=list[WorkerOut])
async def list_workers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    result = await db.execute(select(User).where(User.role == "worker"))
    return result.scalars().all()


@router.get("/{worker_id}", response_model=WorkerOut)
async def get_worker(
    worker_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    result = await db.execute(select(User).where(User.id == worker_id, User.role == "worker"))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    return worker


@router.post("/", response_model=WorkerOut)
async def create_worker(
    body: WorkerCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ese email ya está registrado")

    worker = User(
        name=body.name,
        email=body.email,
        password_hash=pwd_context.hash(body.password),
        role=body.role,
        active=True
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)
    return worker


@router.patch("/{worker_id}", response_model=WorkerOut)
async def update_worker(
    worker_id: int,
    body: WorkerUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    result = await db.execute(select(User).where(User.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")

    if body.name is not None:
        worker.name = body.name
    if body.email is not None:
        worker.email = body.email
    if body.active is not None:
        worker.active = body.active
    if body.password is not None:
        worker.password_hash = pwd_context.hash(body.password)

    await db.commit()
    await db.refresh(worker)
    return worker