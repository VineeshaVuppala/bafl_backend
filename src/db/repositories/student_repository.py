from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.db.models.student import Student

class StudentRepository:
    @staticmethod
    def create(db: Session, student: Student) -> Student:
        db.add(student)
        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def get_by_id(db: Session, student_id: int) -> Optional[Student]:
        return db.scalar(select(Student).where(Student.id == student_id))

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Student]:
        return list(db.scalars(select(Student).offset(skip).limit(limit)).all())

    @staticmethod
    def get_by_batch(db: Session, batch_id: int) -> List[Student]:
        return list(db.scalars(select(Student).where(Student.batch_id == batch_id)).all())

    @staticmethod
    def update(db: Session, student: Student, update_data: dict) -> Student:
        for key, value in update_data.items():
            setattr(student, key, value)
        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def delete(db: Session, student: Student) -> None:
        db.delete(student)
        db.commit()
