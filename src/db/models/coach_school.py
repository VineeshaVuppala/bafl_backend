from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from src.db.database import Base


class CoachSchool(Base):
    __tablename__ = "coach_schools"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    coach_id = Column(Integer, ForeignKey("coaches.id", ondelete="CASCADE"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    coach = relationship("Coach", back_populates="school_assignments")
    school = relationship("School", back_populates="coach_assignments")

    __table_args__ = (
        UniqueConstraint("coach_id", "school_id", name="uq_coach_schools_coach_school"),
    )

    def __repr__(self) -> str:
        return f"<CoachSchool(coach_id={self.coach_id}, school_id={self.school_id})>"
