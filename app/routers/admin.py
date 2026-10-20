from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_admin
from app.models import User, UserRole
from app.schemas import UserRead

router = APIRouter(prefix="/admin", tags=["Administração"])


@router.get(
    "/users",
    response_model=list[UserRead],
    summary="Listar todos os utilizadores (apenas admin)",
)
async def list_users(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


@router.post(
    "/promote/{user_id}",
    response_model=UserRead,
    summary="Promover utilizador a administrador (apenas admin)",
)
async def promote_user(
    user_id: str,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    from fastapi import HTTPException, status

    try:
        uid = _uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido.")

    user = await db.get(User, uid)
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado.")

    user.role = UserRole.admin
    await db.commit()
    await db.refresh(user)
    return user