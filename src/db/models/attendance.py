from sqlalchemy import (
    Column,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    UniqueConstraint,
    func,
    String,
)
from sqlalchemy.orm import relationship
import enum

from src.db.database import Base


class AttendanceStatus(str, enum.Enum):
    PRESENT = "Present"
    ABSENT = "Absent"


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    taken_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (
        UniqueConstraint("school_id", "date", name="uix_school_date"),
    )

    # Relationships
    school = relationship("School", back_populates="attendance_sessions")
    taker = relationship("User")
    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan", lazy="selectin")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uix_session_student"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(SQLEnum(AttendanceStatus), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("AttendanceSession", back_populates="records")
    student = relationship("Student", back_populates="attendance_records")


class CoachAttendance(Base):
    __tablename__ = "coach_attendance"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    coach_id = Column(Integer, ForeignKey("coaches.id", ondelete="SET NULL"), nullable=True, index=True)
    coach_name = Column(String(150), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    school_name = Column(String(150), nullable=False)
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    coach = relationship("Coach", back_populates="coach_attendance")
    school = relationship("School", back_populates="coach_attendance")
    
