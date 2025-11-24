from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from src.db.database import Base


class CoachBatch(Base):
    __tablename__ = "coach_batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    coach_id = Column(Integer, ForeignKey("coaches.id", ondelete="CASCADE"), nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    coach = relationship("Coach", back_populates="batch_assignments")
    batch = relationship("Batch", back_populates="coach_assignments")

    __table_args__ = (
        UniqueConstraint("coach_id", "batch_id", name="uq_coach_batches_coach_batch"),
    )

    def __repr__(self) -> str:
        return f"<CoachBatch(coach_id={self.coach_id}, batch_id={self.batch_id})>"
