from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.db.models.coach_school import CoachSchool


class CoachSchoolRepository:
    @staticmethod
    def create(db: Session, assignment: CoachSchool) -> CoachSchool:
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment

    @staticmethod
    def get_assignment(db: Session, coach_id: int, school_id: int) -> Optional[CoachSchool]:
        stmt = select(CoachSchool).where(
            CoachSchool.coach_id == coach_id,
            CoachSchool.school_id == school_id,
        )
        return db.scalar(stmt)

    @staticmethod
    def get_schools_for_coach(db: Session, coach_id: int) -> List[CoachSchool]:
        stmt = select(CoachSchool).where(CoachSchool.coach_id == coach_id)
        return list(db.scalars(stmt).all())

    @staticmethod
    def delete(db: Session, assignment: CoachSchool) -> None:
        db.delete(assignment)
        db.commit()
