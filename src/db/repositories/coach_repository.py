from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.db.models.coach import Coach

class CoachRepository:
    @staticmethod
    def create(db: Session, coach: Coach) -> Coach:
        db.add(coach)
        db.commit()
        db.refresh(coach)
        return coach

    @staticmethod
    def get_by_id(db: Session, coach_id: int) -> Optional[Coach]:
        return db.scalar(select(Coach).where(Coach.id == coach_id))

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[Coach]:
        return db.scalar(select(Coach).where(Coach.username == username))
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Coach]:
        return list(db.scalars(select(Coach).offset(skip).limit(limit)).all())

    @staticmethod
    def get_by_school(db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[Coach]:
        from src.db.models.coach_school import CoachSchool

        stmt = select(Coach).join(CoachSchool).where(CoachSchool.school_id == school_id).offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    @staticmethod
    def update(db: Session, coach: Coach, update_data: dict) -> Coach:
        for key, value in update_data.items():
            setattr(coach, key, value)
        db.commit()
        db.refresh(coach)
        return coach

    @staticmethod
    def delete(db: Session, coach: Coach) -> None:
        db.delete(coach)
        db.commit()
