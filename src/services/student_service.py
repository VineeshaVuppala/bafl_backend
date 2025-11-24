"""Student service with validation and relationship handling."""
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from src.db.models.physical_assessment import PhysicalAssessmentDetail, PhysicalAssessmentSession
from src.db.models.student import Student
from src.db.repositories.batch_repository import BatchRepository
from src.db.repositories.physical_results_repository import PhysicalResultsRepository
from src.db.repositories.physical_session_repository import PhysicalSessionRepository
from src.db.repositories.student_repository import StudentRepository
from src.schemas.student import StudentCreate, StudentUpdate


class StudentService:
    """Service layer for student operations."""

    @staticmethod
    def _normalize_relationships(
        db: Session,
        base_data: Dict[str, Any],
        existing: Optional[Student] = None,
    ) -> Dict[str, Any]:
        """Validate and normalize foreign key relationships for a student."""

        update_data: Dict[str, Any] = {}

        target_batch_id = base_data.get("batch_id", existing.batch_id if existing else None)

        if target_batch_id is not None:
            batch = BatchRepository.get_by_id(db, target_batch_id)
            if not batch:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Batch with ID {target_batch_id} not found",
                )
            update_data["batch_id"] = target_batch_id

        # Copy through any non-relational fields untouched
        deprecated_keys = {"school_id", "coach_id"}
        for key, value in base_data.items():
            if key not in ("batch_id", *deprecated_keys):
                update_data[key] = value

        return update_data

    @staticmethod
    def create_student(db: Session, student_data: StudentCreate) -> Student:
        payload = student_data.model_dump()
        normalized = StudentService._normalize_relationships(db, payload)
        student = Student(**normalized)
        return StudentRepository.create(db, student)

    @staticmethod
    def get_student(db: Session, student_id: int) -> Student:
        student = StudentRepository.get_by_id(db, student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student with ID {student_id} not found",
            )
        return student

    @staticmethod
    def get_all_students(db: Session, skip: int = 0, limit: int = 100) -> list[Student]:
        return StudentRepository.get_all(db, skip, limit)

    @staticmethod
    def get_students_by_batch(db: Session, batch_id: int) -> list[Student]:
        batch = BatchRepository.get_by_id(db, batch_id)
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch with ID {batch_id} not found",
            )
        return StudentRepository.get_by_batch(db, batch_id)

    @staticmethod
    def update_student(db: Session, student_id: int, student_data: StudentUpdate) -> Student:
        student = StudentService.get_student(db, student_id)
        payload = student_data.model_dump(exclude_unset=True)
        normalized = StudentService._normalize_relationships(db, payload, existing=student)
        if not normalized:
            return student
        updated = StudentRepository.update(db, student, normalized)
        return updated

    @staticmethod
    def delete_student(db: Session, student_id: int) -> bool:
        student = StudentService.get_student(db, student_id)
        StudentRepository.delete(db, student)
        return True

    @staticmethod
    def change_batch(db: Session, student_id: int, new_batch_id: int) -> Dict[str, Any]:
        student = StudentService.get_student(db, student_id)
        old_batch_id = student.batch_id

        if old_batch_id == new_batch_id:
            return {
                "message": "Student already in this batch",
                "student": {
                    "student_id": student.id,
                    "student_name": student.name,
                    "old_batch_id": old_batch_id,
                    "new_batch_id": new_batch_id,
                },
            }

        # Verify new batch exists
        new_batch = BatchRepository.get_by_id(db, new_batch_id)
        if not new_batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch with ID {new_batch_id} not found",
            )

        # Update student
        student.batch_id = new_batch_id
        db.commit()
        db.refresh(student)

        # Handle future sessions
        today = datetime.now().date()

        # 1. Remove from future sessions of old batch
        if old_batch_id:
            old_batch_sessions = db.scalars(
                select(PhysicalAssessmentSession).where(
                    PhysicalAssessmentSession.batch_id == old_batch_id,
                    PhysicalAssessmentSession.date_of_session >= today,
                )
            ).all()

            for session in old_batch_sessions:
                db.execute(
                    delete(PhysicalAssessmentDetail).where(
                        PhysicalAssessmentDetail.session_id == session.id,
                        PhysicalAssessmentDetail.student_id == student_id,
                    )
                )

        # 2. Add to future sessions of new batch
        new_batch_sessions = db.scalars(
            select(PhysicalAssessmentSession).where(
                PhysicalAssessmentSession.batch_id == new_batch_id,
                PhysicalAssessmentSession.date_of_session >= today,
            )
        ).all()

        for session in new_batch_sessions:
            # Check if already exists
            exists = db.scalar(
                select(PhysicalAssessmentDetail).where(
                    PhysicalAssessmentDetail.session_id == session.id,
                    PhysicalAssessmentDetail.student_id == student_id,
                )
            )
            if not exists:
                new_detail = PhysicalAssessmentDetail(
                    session_id=session.id,
                    student_id=student_id,
                    is_present=False,  # Default
                )
                db.add(new_detail)

        db.commit()

        return {
            "message": "Student batch reassigned. Future sessions updated.",
            "student": {
                "student_id": student.id,
                "student_name": student.name,
                "old_batch_id": old_batch_id,
                "new_batch_id": new_batch_id,
            },
        }
