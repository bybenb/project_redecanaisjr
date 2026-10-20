from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.engine import make_url

from app.config import settings



class Base(DeclarativeBase):
    """Classe base para todos os modelos SQLAlchemy."""
    pass



_db_url = settings.DATABASE_URL
if "asyncpg" in _db_url:
    parsed = make_url(_db_url)
    bad_keys = {"sslmode", "channel_binding"}
    clean_query = {k: v for k, v in parsed.query.items() if k not in bad_keys}
    parsed = parsed.set(query=clean_query)
    _db_url = parsed.render_as_string(hide_password=False)




engine = create_async_engine(
    _db_url,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,  
    pool_size=5,
    max_overflow=10,
    connect_args={"ssl": "require"},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injetada nas rotas para obter uma sessão de DB."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise