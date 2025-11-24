from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.db.models.coach_batch import CoachBatch


class CoachBatchRepository:
    @staticmethod
    def create(db: Session, assignment: CoachBatch) -> CoachBatch:
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment

    @staticmethod
    def get_assignment(db: Session, coach_id: int, batch_id: int) -> Optional[CoachBatch]:
        stmt = select(CoachBatch).where(
            CoachBatch.coach_id == coach_id,
            CoachBatch.batch_id == batch_id,
        )
        return db.scalar(stmt)

    @staticmethod
    def get_batches_for_coach(db: Session, coach_id: int) -> List[CoachBatch]:
        stmt = select(CoachBatch).where(CoachBatch.coach_id == coach_id)
        return list(db.scalars(stmt).all())

    @staticmethod
    def delete(db: Session, assignment: CoachBatch) -> None:
        db.delete(assignment)
        db.commit()
