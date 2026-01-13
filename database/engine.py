import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, event
from pgvector.asyncpg import register_vector
from logging import Logger

# Get env vars
POSTGRES_USER = os.getenv("POSTGRES_USER", "alethic")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "alethic_dev_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "alethic_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# log for debugging purposes
logger = Logger("database_engine")
logger.info(f"Connecting to database at {DATABASE_URL}")

db_engine = create_async_engine(DATABASE_URL, echo=False)


# Listen for the 'connect' event to register pgvector
@event.listens_for(db_engine.sync_engine, "connect")
def connect(dbapi_connection, connection_record):
    dbapi_connection.run_async(register_vector)


# Create async session maker to be used throughout the application
AsyncSessionLocal = async_sessionmaker(
    db_engine, class_=AsyncSession, expire_on_commit=False
)


# Base class for declarative models
class Base(DeclarativeBase):
    pass


# Dependency to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# Function to initialize the database (create tables, extensions, etc.)
async def init_db():
    async with db_engine.begin() as conn:
        # Create pgvector extension if not exists
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


# Function to close database connections
async def close_db():
    """Close database engine and connections."""
    await db_engine.dispose()
