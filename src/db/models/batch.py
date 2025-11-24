from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from src.db.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    batch_name = Column(String(150), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    school = relationship("School", back_populates="batches")
    students = relationship("Student", back_populates="batch", cascade="all, delete-orphan")
    physical_sessions = relationship("PhysicalAssessmentSession", back_populates="batch")
    coach_assignments = relationship("CoachBatch", back_populates="batch", cascade="all, delete-orphan")
    schedules = relationship("BatchSchedule", back_populates="batch", cascade="all, delete-orphan")

    @property
    def name(self) -> str:
        return self.batch_name

    @name.setter
    def name(self, value: str) -> None:
        self.batch_name = value

    @property
    def coach_id(self) -> int | None:
        assignment = self.coach_assignments[0] if self.coach_assignments else None
        return assignment.coach_id if assignment else None
