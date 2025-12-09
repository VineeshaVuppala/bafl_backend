from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
from src.db.database import Base


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), unique=True, nullable=False)
    address = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    batches = relationship("Batch", back_populates="school", cascade="all, delete-orphan")
    coach_assignments = relationship("CoachSchool", back_populates="school", cascade="all, delete-orphan")
    coaches = association_proxy("coach_assignments", "coach")
    physical_sessions = relationship("PhysicalAssessmentSession", back_populates="school")
    attendance_sessions = relationship("AttendanceSession", back_populates="school")
    coach_attendance = relationship("CoachAttendance", back_populates="school", cascade="all, delete-orphan", lazy="selectin")
