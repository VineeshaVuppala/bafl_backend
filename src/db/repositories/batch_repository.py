from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.db.models.batch import Batch
from src.db.models.coach_batch import CoachBatch

class BatchRepository:
    @staticmethod
    def create(db: Session, batch: Batch) -> Batch:
        db.add(batch)
        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def get_by_id(db: Session, batch_id: int) -> Optional[Batch]:
        return db.scalar(select(Batch).where(Batch.id == batch_id))

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Batch]:
        return list(db.scalars(select(Batch).offset(skip).limit(limit)).all())

    @staticmethod
    def get_by_school(db: Session, school_id: int) -> List[Batch]:
        return list(db.scalars(select(Batch).where(Batch.school_id == school_id)).all())

    @staticmethod
    def get_by_coach(db: Session, coach_id: int) -> List[Batch]:
        stmt = (
            select(Batch)
            .join(CoachBatch, CoachBatch.batch_id == Batch.id)
            .where(CoachBatch.coach_id == coach_id)
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def update(db: Session, batch: Batch, update_data: dict) -> Batch:
        for key, value in update_data.items():
            setattr(batch, key, value)
        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def delete(db: Session, batch: Batch) -> None:
        db.delete(batch)
        db.commit()
