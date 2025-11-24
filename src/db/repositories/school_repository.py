from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.db.models.school import School

class SchoolRepository:
    @staticmethod
    def create(db: Session, school: School) -> School:
        db.add(school)
        db.commit()
        db.refresh(school)
        return school

    @staticmethod
    def get_by_id(db: Session, school_id: int) -> Optional[School]:
        return db.scalar(select(School).where(School.id == school_id))

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[School]:
        return list(db.scalars(select(School).offset(skip).limit(limit)).all())

    @staticmethod
    def update(db: Session, school: School, update_data: dict) -> School:
        for key, value in update_data.items():
            setattr(school, key, value)
        db.commit()
        db.refresh(school)
        return school

    @staticmethod
    def delete(db: Session, school: School) -> None:
        db.delete(school)
        db.commit()
