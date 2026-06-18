from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User
from app.config import settings

bearer = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return user


async def get_current_manager(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "manager":
        raise HTTPException(status_code=403, detail="Acceso solo para supervisores")
    return current_user

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        print("PAYLOAD:", payload)
        user_id = payload.get("sub")
        print("USER_ID:", user_id)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        user_id = int(user_id)
    except JWTError as e:
        print("JWT ERROR:", e)
        raise HTTPException(status_code=401, detail="Token inválido")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user

async def get_current_manager(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "manager":
        raise HTTPException(status_code=403, detail="Acceso solo para supervisores")
    return current_user