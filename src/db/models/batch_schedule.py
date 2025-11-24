from sqlalchemy import Column, Integer, ForeignKey, String, Time, DateTime, func
from sqlalchemy.orm import relationship

from src.db.database import Base


class BatchSchedule(Base):
    __tablename__ = "batch_schedules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(String(20), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    batch = relationship("Batch", back_populates="schedules")

    def __repr__(self) -> str:
        return (
            f"<BatchSchedule(batch_id={self.batch_id}, day_of_week='{self.day_of_week}', "
            f"start_time={self.start_time}, end_time={self.end_time})>"
        )
