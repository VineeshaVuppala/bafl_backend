from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.db.models.batch_schedule import BatchSchedule


class BatchScheduleRepository:
    @staticmethod
    def create(db: Session, schedule: BatchSchedule) -> BatchSchedule:
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def get_by_id(db: Session, schedule_id: int) -> Optional[BatchSchedule]:
        stmt = select(BatchSchedule).where(BatchSchedule.id == schedule_id)
        return db.scalar(stmt)

    @staticmethod
    def get_for_batch(db: Session, batch_id: int) -> List[BatchSchedule]:
        stmt = select(BatchSchedule).where(BatchSchedule.batch_id == batch_id)
        return list(db.scalars(stmt).all())

    @staticmethod
    def delete(db: Session, schedule: BatchSchedule) -> None:
        db.delete(schedule)
        db.commit()
