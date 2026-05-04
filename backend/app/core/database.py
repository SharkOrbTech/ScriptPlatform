from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, Boolean
from datetime import datetime
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class ScriptDB(Base):
    __tablename__ = "scripts"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    genre = Column(String, default="")
    logline = Column(Text, default="")
    synopsis = Column(Text, default="")
    characters = Column(JSON, default=list)
    episodes = Column(JSON, default=list)
    theme = Column(Text, default="")
    emotional_tone = Column(String, default="")
    target_audience = Column(String, default="")
    style = Column(String, default="")
    status = Column(String, default="completed")
    progress = Column(Float, default=100.0)
    copyright_risk = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TrendDB(Base):
    __tablename__ = "trends"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)
    category = Column(String, default="")
    heat = Column(Integer, default=0)
    description = Column(Text, default="")
    cover_url = Column(String, default="")
    url = Column(String, default="")
    tags = Column(JSON, default=list)
    scraped_at = Column(DateTime, default=datetime.utcnow)


class TaskDB(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    task_type = Column(String, nullable=False)
    status = Column(String, default="pending")
    progress = Column(Float, default=0.0)
    result = Column(JSON, nullable=True)
    error = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
