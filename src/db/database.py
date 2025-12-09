"""
Database connection and session management.
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from src.core.config import settings
from src.core.logging import db_logger


# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG,
    pool_pre_ping=True
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()

# Import all models to register with Base
from src.db.models.user import User, RefreshToken
from src.db.models.permission import Permission, UserPermission
from src.db.models.school import School
from src.db.models.coach import Coach
from src.db.models.batch import Batch
from src.db.models.batch_schedule import BatchSchedule
from src.db.models.coach_batch import CoachBatch
from src.db.models.coach_school import CoachSchool
from src.db.models.student import Student
from src.db.models.physical_assessment import PhysicalAssessmentSession, PhysicalAssessmentDetail
from src.db.models.attendance import AttendanceSession, AttendanceRecord, CoachAttendance


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        db_logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()


def init_database() -> None:
    """Initialize database tables."""
    db_logger.info("Initializing database...")
    try:
        Base.metadata.create_all(bind=engine)
        db_logger.info("Database initialized successfully")
    except Exception as e:
        db_logger.error(f"Failed to initialize database: {str(e)}")
        raise
