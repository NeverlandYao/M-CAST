from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.pool import NullPool
import datetime
import uuid
import os
import traceback
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=env_path)
load_dotenv() # Fallback

# Use environment variable
# Note: For asyncpg, we need to use postgresql+asyncpg://
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("WARNING: DATABASE_URL environment variable is not set. Database operations will fail.")
    # Fallback to prevent immediate crash on import, will fail on connection
    DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"
else:
    # Ensure the driver is correct for async
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

    # Mask password for logging
    safe_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "..."
    print(f"DEBUG: DATABASE_URL loaded (host/db): {safe_url}")
    
    # Remove unsupported query parameters for asyncpg
    if "?" in DATABASE_URL:
        # Remove pgbouncer=true
        DATABASE_URL = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
        # Remove connection_limit (Prisma specific)
        DATABASE_URL = DATABASE_URL.replace("?connection_limit=1", "").replace("&connection_limit=1", "")
        
        # If ? is at the end or followed by empty, strip it
        if DATABASE_URL.endswith("?"):
            DATABASE_URL = DATABASE_URL[:-1]

# Create engine with pre-ping to handle closed connections
# Serverless 优化: 使用 NullPool 禁用连接池，防止连接耗尽
engine = create_async_engine(
    DATABASE_URL, 
    echo=True,
    pool_pre_ping=True,
    poolclass=NullPool,
    # If using Supabase Transaction Pooler (port 6543), un-comment the next line:
    connect_args={
        "server_settings": {"jit": "off"},
        "statement_cache_size": 0 # Required for Supabase Transaction Pooler (PgBouncer)
    }
)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

class ChatLog(Base):
    __tablename__ = "chatlog"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    student_id = Column(String, nullable=True)  # Added student_id
    role = Column(String)  # 'user' or 'agent'
    content = Column(Text)
    group_type = Column(String, default="experimental")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ControlChatLog(Base):
    __tablename__ = "control_chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    student_id = Column(String, nullable=True)
    role = Column(String)  # 'user' or 'agent'
    content = Column(Text)
    group_type = Column(String, default="control")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

async def init_db():
    print("DEBUG: Initializing database...")
    try:
        async with engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
        print("DEBUG: Database tables created/verified successfully.")
    except Exception as e:
        print(f"ERROR: Database initialization failed: {e}")
        traceback.print_exc()
        # 不抛出异常，允许应用启动，但在后续操作中可能会报错

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def log_message(session: AsyncSession, user_id: uuid.UUID, role: str, content: str, group_type: str = "experimental", student_id: str = None):
    try:
        # All conversations are recorded in the chatlog table (ChatLog model)
        new_log = ChatLog(user_id=user_id, role=role, content=content, group_type=group_type, student_id=student_id)
        
        session.add(new_log)
        await session.commit()
        print(f"DEBUG: Message logged successfully for student_id={student_id}, role={role} to chatlog table")
    except Exception as e:
        print(f"ERROR: Failed to log message: {e}")
        traceback.print_exc()
        await session.rollback()
