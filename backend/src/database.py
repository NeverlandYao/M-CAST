from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, text
from sqlalchemy.dialects.postgresql import UUID
import datetime
import uuid
import os
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

# Create engine with pre-ping to handle closed connections
engine = create_async_engine(
    DATABASE_URL, 
    echo=True,
    pool_pre_ping=True,
    # If using Supabase Transaction Pooler (port 6543), un-comment the next line:
    # connect_args={"server_settings": {"jit": "off"}} 
)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

class ChatLog(Base):
    __tablename__ = "chat_logs"

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
    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def log_message(session: AsyncSession, user_id: uuid.UUID, role: str, content: str, group_type: str = "experimental", student_id: str = None):
    try:
        if group_type == "control":
            new_log = ControlChatLog(user_id=user_id, role=role, content=content, group_type=group_type, student_id=student_id)
        else:
            new_log = ChatLog(user_id=user_id, role=role, content=content, group_type=group_type, student_id=student_id)
        
        session.add(new_log)
        await session.commit()
    except Exception as e:
        print(f"Error logging message: {e}")
        await session.rollback()
