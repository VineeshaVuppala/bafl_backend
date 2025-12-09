from __future__ import annotations

from typing import Dict, List, Set

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.core.security import PasswordHandler
from src.db.models.batch import Batch
from src.db.models.coach import Coach
from src.db.models.coach_batch import CoachBatch
from src.db.models.coach_school import CoachSchool
from src.db.models.school import School
from src.db.models.user import User
from src.db.repositories.batch_repository import BatchRepository
from src.db.repositories.coach_repository import CoachRepository
from src.db.repositories.school_repository import SchoolRepository
from src.db.repositories.user_repository import UserRepository
from src.schemas.coach import (
    CoachBatchAssignment,
    CoachContractDetails,
    CoachCreateRequest,
    CoachSchoolAssignment,
    CoachUpdateRequest,
)
from src.db.models.user import UserRole


class CoachService:
    """Business logic for coach resources aligned with the consolidated contract."""

    @staticmethod
    def _ensure_username_available(db: Session, username: str) -> None:
        if CoachRepository.get_by_username(db, username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already in use",
            )

    @staticmethod
    def _get_coach_or_404(db: Session, coach_id: int) -> Coach:
        coach = CoachRepository.get_by_id(db, coach_id)
        if not coach:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach not found")
        return coach

    @staticmethod
    def _fetch_batches(db: Session, batch_ids: Set[int]) -> Dict[int, Batch]:
        batches: Dict[int, Batch] = {}
        for batch_id in batch_ids:
            batch = BatchRepository.get_by_id(db, batch_id)
            if not batch:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Batch with ID {batch_id} not found",
                )
            batches[batch_id] = batch
        return batches

    @staticmethod
    def _fetch_schools(db: Session, school_ids: Set[int]) -> Dict[int, School]:
        schools: Dict[int, School] = {}
        for school_id in school_ids:
            school = SchoolRepository.get_by_id(db, school_id)
            if not school:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"School with ID {school_id} not found",
                )
            schools[school_id] = school
        return schools

    @staticmethod
    def _sync_school_assignments(db: Session, coach: Coach, target_ids: Set[int]) -> None:
        current = {assignment.school_id: assignment for assignment in list(coach.school_assignments)}

        for school_id, assignment in current.items():
            if school_id not in target_ids:
                db.delete(assignment)

        for school_id in target_ids:
            if school_id not in current:
                db.add(CoachSchool(coach_id=coach.id, school_id=school_id))

        db.flush()
        db.expire(coach, ["school_assignments"])

    @staticmethod
    def _sync_batch_assignments(db: Session, coach: Coach, target_ids: Set[int]) -> None:
        current = {assignment.batch_id: assignment for assignment in list(coach.batch_assignments)}

        for batch_id, assignment in current.items():
            if batch_id not in target_ids:
                db.delete(assignment)

        for batch_id in target_ids:
            if batch_id not in current:
                db.add(CoachBatch(coach_id=coach.id, batch_id=batch_id))

        db.flush()
        db.expire(coach, ["batch_assignments"])

    @staticmethod
    def _build_contract_details(coach: Coach) -> CoachContractDetails:
        schools: List[CoachSchoolAssignment] = []
        for assignment in coach.school_assignments:
            school = assignment.school
            if not school:
                continue
            schools.append(
                CoachSchoolAssignment(
                    school_id=school.id,
                    school_name=school.name,
                )
            )

        batches: List[CoachBatchAssignment] = []
        for assignment in coach.batch_assignments:
            batch = assignment.batch
            if not batch:
                continue
            school = batch.school
            batches.append(
                CoachBatchAssignment(
                    batch_id=batch.id,
                    batch_name=batch.batch_name,
                    school_id=school.id if school else batch.school_id,
                    school_name=school.name if school else "",
                )
            )

        schools.sort(key=lambda item: item.school_name.lower())
        batches.sort(key=lambda item: (item.school_name.lower(), item.batch_name.lower()))

        return CoachContractDetails(
            coach_id=coach.id,
            name=coach.name,
            schools=schools,
            batches=batches,
        )

    @staticmethod
    def create_coach(db: Session, payload: CoachCreateRequest) -> CoachContractDetails:
        CoachService._ensure_username_available(db, payload.username)

        requested_school_ids: Set[int] = set(payload.schools or [])
        requested_batch_ids: Set[int] = set(payload.batches or [])

        batch_map = CoachService._fetch_batches(db, requested_batch_ids)
        for batch in batch_map.values():
            requested_school_ids.add(batch.school_id)

        if requested_school_ids:
            CoachService._fetch_schools(db, requested_school_ids)

        hashed_password = PasswordHandler.hash(payload.password)

        # Use nested transaction if one exists, or start new one
        # Since we are in a service method called by API which might have dependency injection of session
        # The session might already be in a transaction or not.
        # However, db.begin() raises error if transaction is already begun.
        # We should use db.begin_nested() if we want a savepoint, or just rely on the outer transaction commit.
        # But here we want to ensure atomicity of this operation.
        # If the session is provided by FastAPI dependency `get_db`, it is usually autocommitted at the end of request if no error?
        # Actually `get_db` yields a session. It does not start a transaction automatically unless we do something.
        # But `db.begin()` fails if one is active.
        # Let's try to use the session directly without `with db.begin():` if we assume the caller handles commit, 
        # OR check if transaction is active.
        # Better pattern: just do the operations and let the caller (or a context manager) handle commit.
        # But the original code used `with db.begin():`.
        # The error "A transaction is already begun on this Session" suggests that somewhere else a transaction was started.
        # It might be `CoachService._ensure_username_available` or `_fetch_batches` doing something? No, they are read operations.
        # Wait, `UserRepository.get_by_username` inside `_ensure_username_available` might be doing something?
        # Let's remove `with db.begin():` and just use `db.commit()` at the end, or rely on the fact that we want to commit here.
        
        try:
            coach = Coach(
                name=payload.name,
                username=payload.username,
                is_active=True,
            )
            coach.password_hash = hashed_password
            db.add(coach)
            db.flush()

            # Sync with User table
            if not UserRepository.get_by_username(db, payload.username):
                user_data = {
                    "name": payload.name,
                    "username": payload.username,
                    "hashed_password": hashed_password,
                    "role": UserRole.COACH,
                    "is_active": True
                }
                user = User(**user_data)
                db.add(user)
                db.flush()

            if requested_school_ids:
                CoachService._sync_school_assignments(db, coach, requested_school_ids)
            if requested_batch_ids:
                CoachService._sync_batch_assignments(db, coach, requested_batch_ids)
            
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(coach)
        return CoachService._build_contract_details(coach)

    @staticmethod
    def list_coaches(db: Session, skip: int = 0, limit: int = 100, school_id: int | None = None) -> List[CoachContractDetails]:
        if school_id is not None:
            coaches = CoachRepository.get_by_school(db, school_id, skip, limit)
        else:
            coaches = CoachRepository.get_all(db, skip, limit)
        return [CoachService._build_contract_details(coach) for coach in coaches]

    @staticmethod
    def get_coach(db: Session, coach_id: int) -> CoachContractDetails:
        coach = CoachService._get_coach_or_404(db, coach_id)
        return CoachService._build_contract_details(coach)

    @staticmethod
    def update_coach(db: Session, coach_id: int, payload: CoachUpdateRequest) -> CoachContractDetails:
        coach = CoachService._get_coach_or_404(db, coach_id)

        update_fields: Dict[str, object] = {}
        if payload.name is not None:
            update_fields["name"] = payload.name
        if payload.password is not None:
            update_fields["password_hash"] = PasswordHandler.hash(payload.password)

        assignments_changed = payload.schools is not None or payload.batches is not None

        if payload.batches is not None:
            target_batch_ids: Set[int] = set(payload.batches)
        else:
            target_batch_ids = {assignment.batch_id for assignment in coach.batch_assignments if assignment.batch_id is not None}

        if payload.schools is not None:
            target_school_ids: Set[int] = set(payload.schools)
        elif payload.batches is not None:
            target_school_ids = set()
        else:
            target_school_ids = {assignment.school_id for assignment in coach.school_assignments if assignment.school_id is not None}

        batch_map = CoachService._fetch_batches(db, target_batch_ids)
        for batch in batch_map.values():
            target_school_ids.add(batch.school_id)

        if target_school_ids:
            CoachService._fetch_schools(db, target_school_ids)

        # Capture old username before update for User sync
        old_username = coach.username

        try:
            if "password_hash" in update_fields:
                coach.password_hash = update_fields.pop("password_hash")  # type: ignore[assignment]
            for field, value in update_fields.items():
                setattr(coach, field, value)

            if assignments_changed:
                CoachService._sync_school_assignments(db, coach, target_school_ids)
                CoachService._sync_batch_assignments(db, coach, target_batch_ids)
            
            # Sync with User table
            user = UserRepository.get_by_username(db, old_username)
            if user:
                if payload.name is not None:
                    user.name = payload.name
                if payload.password is not None:
                    user.hashed_password = PasswordHandler.hash(payload.password)
                # If username is changing, we need to check availability (already done for coach, but user table might have conflict if not same)
                # But since we enforce username uniqueness across system (ideally), and we checked coach table.
                # We should also check user table if username is changing.
                # However, _ensure_username_available only checks Coach table.
                # Let's assume 1-to-1 mapping.
                # Note: CoachService._ensure_username_available only checks CoachRepository.
                # If we change username here, we should update user too.
                # But CoachUpdateRequest doesn't have username field in the schema provided in context?
                # Let's check CoachUpdateRequest schema.
                pass 
            
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(coach)
        return CoachService._build_contract_details(coach)

    @staticmethod
    def delete_coach(db: Session, coach_id: int) -> None:
        coach = CoachService._get_coach_or_404(db, coach_id)
        username = coach.username
        try:
            db.delete(coach)
            
            # Sync delete with User table
            user = UserRepository.get_by_username(db, username)
            if user:
                db.delete(user)
            
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def sync_coach(db: Session, user: User) -> None:
        """No-op: users and coaches remain separate entities in the new contract."""
        return
