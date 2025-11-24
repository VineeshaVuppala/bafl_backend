from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.db.models.physical_assessment import PhysicalAssessmentSession

class PhysicalSessionRepository:
    @staticmethod
    def create(db: Session, session: PhysicalAssessmentSession) -> PhysicalAssessmentSession:
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_by_id(db: Session, session_id: int) -> Optional[PhysicalAssessmentSession]:
        return db.scalar(select(PhysicalAssessmentSession).where(PhysicalAssessmentSession.id == session_id))

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[PhysicalAssessmentSession]:
        return list(db.scalars(select(PhysicalAssessmentSession).offset(skip).limit(limit)).all())

    @staticmethod
    def get_by_batch(db: Session, batch_id: int) -> List[PhysicalAssessmentSession]:
        return list(db.scalars(select(PhysicalAssessmentSession).where(PhysicalAssessmentSession.batch_id == batch_id)).all())
    
    @staticmethod
    def get_by_coach(db: Session, coach_id: int) -> List[PhysicalAssessmentSession]:
        return list(db.scalars(select(PhysicalAssessmentSession).where(PhysicalAssessmentSession.coach_id == coach_id)).all())

    @staticmethod
    def update(db: Session, session: PhysicalAssessmentSession, update_data: dict) -> PhysicalAssessmentSession:
        for key, value in update_data.items():
            setattr(session, key, value)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def delete(db: Session, session: PhysicalAssessmentSession) -> None:
        db.delete(session)
        db.commit()
