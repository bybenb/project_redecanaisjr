from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import Token, UserCreate, UserRead
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registar novo utilizador",
)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # 1. Verificar se o e-mail já existe
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com este e-mail.",
        )

    # 2. Criar utilizador
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # TODO (futuro): enfileirar e-mail de boas-vindas em email_queue
    # TODO (futuro): gerar verification_token

    return user


@router.post("/login", response_model=Token, summary="Login do utilizador")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada.",
        )

    
    
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(subject=user.id)
    return Token(access_token=token)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Obter dados do utilizador autenticado",
)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user