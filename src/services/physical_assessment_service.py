from datetime import datetime
from typing import Dict, Iterable, Sequence, List

from fastapi import HTTPException, status
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.logging import api_logger, db_logger
from src.db.models.batch import Batch
from src.db.models.physical_assessment import PhysicalAssessmentDetail, PhysicalAssessmentSession
from src.db.models.student import Student
from src.db.models.user import UserRole, User
from src.db.repositories.batch_repository import BatchRepository
from src.db.repositories.coach_repository import CoachRepository
from src.db.repositories.physical_results_repository import PhysicalResultsRepository
from src.db.repositories.physical_session_repository import PhysicalSessionRepository
from src.db.repositories.school_repository import SchoolRepository
from src.db.repositories.student_repository import StudentRepository
from src.schemas.batch import BatchSummary, BatchScheduleItem
from src.schemas.physical_assessment import (
    PhysicalAssessmentResultResponse,
    PhysicalAssessmentResultUpdate,
    PhysicalAssessmentSessionCreate,
    PhysicalAssessmentSessionResponse,
    PhysicalAssessmentSessionUpdate,
    PhysicalAssessmentSessionWithResultsCreate,
    PreCreateResponse,
    PreCreateBatch,
    PreCreateSchedule,
    PreCreateCoach,
    PreCreateStudent,
    PhysicalAssessmentSessionAdminViewResponse,
    PhysicalAssessmentSessionAdminView,
)
from src.db.models.coach import Coach
from src.db.models.coach_batch import CoachBatch


class PhysicalAssessmentService:
    @staticmethod
    def _build_batch_summary(batch: Batch | None) -> BatchSummary | None:
        if batch is None:
            return None
        school = batch.school
        return BatchSummary(
            batch_id=batch.id,
            batch_name=batch.batch_name,
            school_id=batch.school_id,
            school_name=school.name if school else "",
        )

    @staticmethod
    def _build_result_response(detail: PhysicalAssessmentDetail) -> PhysicalAssessmentResultResponse:
        return PhysicalAssessmentResultResponse(
            id=detail.id,
            session_id=detail.session_id,
            student_id=detail.student_id,
            student=detail.student,
            discipline=detail.discipline,
            curl_up=detail.curl_up,
            push_up=detail.push_up,
            sit_and_reach=detail.sit_and_reach,
            walk_600m=detail.walk_600m,
            dash_50m=detail.dash_50m,
            bow_hold=detail.bow_hold,
            plank=detail.plank,
            is_present=detail.is_present,
            created_at=detail.created_at,
            updated_at=detail.updated_at,
        )

    @staticmethod
    def _build_session_response(
        db: Session,
        session: PhysicalAssessmentSession,
        *,
        include_results: bool = True,
    ) -> PhysicalAssessmentSessionResponse:
        batch_summary = PhysicalAssessmentService._build_batch_summary(session.batch)

        batch_schedule = []
        if session.batch and session.batch.schedules:
            batch_schedule = [
                BatchScheduleItem(
                    schedule_id=s.id,
                    day_of_week=s.day_of_week,
                    start_time=s.start_time,
                    end_time=s.end_time,
                )
                for s in session.batch.schedules
            ]

        results: List[PhysicalAssessmentResultResponse] = []
        if include_results:
            details = list(session.results)
            if not details:
                details = PhysicalResultsRepository.get_by_session(db, session.id)
            results = [PhysicalAssessmentService._build_result_response(detail) for detail in details]

        return PhysicalAssessmentSessionResponse(
            id=session.id,
            coach_id=session.coach_id,
            school_id=session.school_id,
            batch_id=session.batch_id,
            date_of_session=session.date_of_session,
            time_of_session=session.time_of_session,
            student_count=session.student_count,
            created_at=session.created_at,
            updated_at=session.updated_at,
            batch=batch_summary,
            school=session.school,
            batch_schedule=batch_schedule,
            results=results,
        )

    @staticmethod
    def serialize_session(
        db: Session,
        session: PhysicalAssessmentSession,
        *,
        include_results: bool = True,
    ) -> PhysicalAssessmentSessionResponse:
        return PhysicalAssessmentService._build_session_response(db, session, include_results=include_results)

    @staticmethod
    def serialize_result(detail: PhysicalAssessmentDetail) -> PhysicalAssessmentResultResponse:
        return PhysicalAssessmentService._build_result_response(detail)

    @staticmethod
    def _resolve_relationships(
        db: Session,
        coach_id: int | None,
        school_id: int | None,
        batch_id: int | None,
    ) -> Dict[str, object]:
        batch = None
        if batch_id is not None:
            batch = BatchRepository.get_by_id(db, batch_id)
            if not batch:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Batch with ID {batch_id} not found",
                )
            if batch.coach_id and coach_id and batch.coach_id != coach_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Coach does not match the batch assignment",
                )
            if batch.school_id is not None:
                if school_id is not None and school_id != batch.school_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Batch and school mismatch",
                    )
                school_id = batch.school_id
            if coach_id is None and batch.coach_id:
                coach_id = batch.coach_id

        coach = None
        if coach_id is not None:
            coach = CoachRepository.get_by_id(db, coach_id)
            if not coach:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Coach with ID {coach_id} not found",
                )
            if coach.school_id and school_id and coach.school_id != school_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Coach and school mismatch",
                )
            if coach.school_id and school_id is None:
                school_id = coach.school_id

        school = None
        if school_id is not None:
            school = SchoolRepository.get_by_id(db, school_id)
            if not school:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"School with ID {school_id} not found",
                )

        return {"coach_id": coach_id, "school_id": school_id, "batch": batch}

    @staticmethod
    def _prepare_default_results(session_id: int, students: Sequence[int]) -> Iterable[PhysicalAssessmentDetail]:
        for student_id in students:
            yield PhysicalAssessmentDetail(
                session_id=session_id,
                student_id=student_id,
                curl_up=0,
                push_up=0,
                sit_and_reach=0.0,
                walk_600m=0.0,
                dash_50m=0.0,
                bow_hold=0.0,
                plank=0.0,
                is_present=True,
            )

    @staticmethod
    def create_session(db: Session, session_data: PhysicalAssessmentSessionCreate) -> PhysicalAssessmentSession:
        refs = PhysicalAssessmentService._resolve_relationships(
            db,
            coach_id=session_data.coach_id,
            school_id=session_data.school_id,
            batch_id=session_data.batch_id,
        )

        payload = session_data.model_dump()
        payload["coach_id"] = refs["coach_id"]
        payload["school_id"] = refs["school_id"]

        batch = refs["batch"]
        student_ids: list[int] = []
        if batch:
            students = StudentRepository.get_by_batch(db, batch.id)
            student_ids = [student.id for student in students]
            expected_count = len(student_ids)
            if expected_count and session_data.student_count != expected_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="student_count must match batch size",
                )
            payload["student_count"] = expected_count

        session = PhysicalAssessmentSession(**payload)
        session = PhysicalSessionRepository.create(db, session)

        if student_ids:
            PhysicalResultsRepository.create_all(
                db,
                list(PhysicalAssessmentService._prepare_default_results(session.id, student_ids)),
            )

        refreshed = PhysicalSessionRepository.get_by_id(db, session.id)
        if refreshed is None:
            refreshed = session
        return PhysicalAssessmentService.serialize_session(db, refreshed)

    @staticmethod
    def create_session_with_results(
        db: Session,
        payload: PhysicalAssessmentSessionWithResultsCreate,
        current_user,
    ) -> PhysicalAssessmentSession:
        if not payload.results:
            raise ValueError("results must be a non-empty list")
        if payload.batch_id is None:
            raise ValueError("batch_id is required when submitting results")

        refs = PhysicalAssessmentService._resolve_relationships(
            db,
            coach_id=payload.coach_id,
            school_id=payload.school_id,
            batch_id=payload.batch_id,
        )

        stmt = select(Student.id).where(Student.batch_id == payload.batch_id).with_for_update()
        student_rows = list(db.execute(stmt).scalars())
        actual_batch_student_ids = set(student_rows)

        if not actual_batch_student_ids:
            raise ValueError("Batch has no students to record results for")

        if len(payload.results) != len({r.student_id for r in payload.results}):
            raise ValueError("Duplicate student entries detected in results payload")

        provided_ids = {r.student_id for r in payload.results}
        invalid_ids = list(provided_ids - actual_batch_student_ids)
        admin_override = bool(getattr(payload, "admin_override", False))
        role = getattr(current_user, "role", None)
        role_value = getattr(role, "value", role)
        is_admin = role_value == UserRole.ADMIN.value

        if invalid_ids and not (admin_override and is_admin):
            raise ValueError(f"Some student_ids do not belong to batch: {invalid_ids}")

        if payload.student_count is not None and payload.student_count != len(actual_batch_student_ids):
            raise ValueError(
                "student_count mismatch: provided={} actual={}".format(
                    payload.student_count,
                    len(actual_batch_student_ids),
                )
            )

        numeric_int_fields = ["curl_up", "push_up"]
        numeric_float_fields = ["sit_and_reach", "walk_600m", "dash_50m", "bow_hold", "plank"]

        results_to_insert: list[dict[str, object]] = []
        for result in payload.results:
            record: dict[str, object] = {
                "student_id": int(result.student_id),
                "discipline": result.discipline,
            }
            any_nonzero = False

            for field in numeric_int_fields:
                value = getattr(result, field, 0) or 0
                try:
                    value = int(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid integer for {field} for student {result.student_id}") from exc
                if value < 0:
                    raise ValueError(f"Negative value for {field} for student {result.student_id}")
                record[field] = value
                if value:
                    any_nonzero = True

            for field in numeric_float_fields:
                value = getattr(result, field, 0.0) or 0.0
                try:
                    value = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid float for {field} for student {result.student_id}") from exc
                if value < 0:
                    raise ValueError(f"Negative value for {field} for student {result.student_id}")
                record[field] = round(value, 2)
                if value:
                    any_nonzero = True

            record["is_present"] = any_nonzero
            results_to_insert.append(record)

        try:
            with db.begin():
                new_session = PhysicalAssessmentSession(
                    coach_id=refs["coach_id"],
                    school_id=refs["school_id"],
                    batch_id=payload.batch_id,
                    date_of_session=payload.date_of_session,
                    student_count=len(actual_batch_student_ids),
                )
                db.add(new_session)
                db.flush()

                for result in results_to_insert:
                    result["session_id"] = new_session.id

                if results_to_insert:
                    db.execute(insert(PhysicalAssessmentDetail), results_to_insert)

                db.refresh(new_session)

            if invalid_ids and admin_override and is_admin:
                api_logger.info(
                    "Admin override by user %s for batch %s invalid student_ids=%s",
                    getattr(current_user, "id", "unknown"),
                    payload.batch_id,
                    invalid_ids,
                )

            refreshed = PhysicalSessionRepository.get_by_id(db, new_session.id)
            if refreshed is None:
                refreshed = new_session
            return PhysicalAssessmentService.serialize_session(db, refreshed)

        except IntegrityError as exc:
            db.rollback()
            db_logger.error("DB integrity error during create_session_with_results: %s", str(exc))
            raise

    @staticmethod
    def get_session(db: Session, session_id: int) -> PhysicalAssessmentSessionResponse | None:
        session = PhysicalSessionRepository.get_by_id(db, session_id)
        if not session:
            return None
        return PhysicalAssessmentService.serialize_session(db, session)

    @staticmethod
    def get_session_model(db: Session, session_id: int) -> PhysicalAssessmentSession | None:
        return PhysicalSessionRepository.get_by_id(db, session_id)

    @staticmethod
    def get_all_sessions(db: Session, skip: int = 0, limit: int = 100) -> list[PhysicalAssessmentSession]:
        return PhysicalSessionRepository.get_all(db, skip, limit)

    @staticmethod
    def update_session(
        db: Session,
        session_id: int,
        session_data: PhysicalAssessmentSessionUpdate,
    ) -> PhysicalAssessmentSessionResponse | None:
        session = PhysicalSessionRepository.get_by_id(db, session_id)
        if not session:
            return None
        payload = session_data.model_dump(exclude_unset=True)
        if not payload:
            return PhysicalAssessmentService.serialize_session(db, session)

        refs = PhysicalAssessmentService._resolve_relationships(
            db,
            coach_id=payload.get("coach_id", session.coach_id),
            school_id=payload.get("school_id", session.school_id),
            batch_id=payload.get("batch_id", session.batch_id),
        )
        payload["coach_id"] = refs["coach_id"]
        payload["school_id"] = refs["school_id"]
        updated = PhysicalSessionRepository.update(db, session, payload)
        return PhysicalAssessmentService.serialize_session(db, updated)

    @staticmethod
    def update_result(
        db: Session,
        result_id: int,
        result_data: PhysicalAssessmentResultUpdate,
    ) -> PhysicalAssessmentResultResponse | None:
        result = PhysicalResultsRepository.get_by_id(db, result_id)
        if not result:
            return None

        payload = result_data.model_dump(exclude_unset=True)
        numeric_fields = [
            "curl_up",
            "push_up",
            "sit_and_reach",
            "walk_600m",
            "dash_50m",
            "bow_hold",
            "plank",
        ]

        for field in numeric_fields:
            if field in payload and payload[field] is None:
                payload[field] = 0.0 if field == "sit_and_reach" else 0

        values = [payload.get(field, getattr(result, field)) for field in numeric_fields]
        payload["is_present"] = any(value for value in values)

        updated = PhysicalResultsRepository.update(db, result, payload)
        return PhysicalAssessmentService.serialize_result(updated)

    @staticmethod
    def get_results_by_session(db: Session, session_id: int) -> list[PhysicalAssessmentResultResponse]:
        details = PhysicalResultsRepository.get_by_session(db, session_id)
        return [PhysicalAssessmentService.serialize_result(detail) for detail in details]

    @staticmethod
    def get_result(db: Session, result_id: int) -> PhysicalAssessmentResultResponse | None:
        detail = PhysicalResultsRepository.get_by_id(db, result_id)
        if not detail:
            return None
        return PhysicalAssessmentService.serialize_result(detail)

    @staticmethod
    def get_pre_create_data(db: Session, user: User) -> PreCreateResponse:
        query = select(Batch)
        
        if user.role == UserRole.COACH:
            coach_profile = getattr(user, "coach_profile", None)
            if not coach_profile:
                return PreCreateResponse(batches=[])
            # Filter batches assigned to this coach
            query = query.join(CoachBatch).filter(CoachBatch.coach_id == coach_profile.id)
        
        batches = db.scalars(query).all()
        
        pre_create_batches = []
        for batch in batches:
            # Schedule
            schedule_list = [
                PreCreateSchedule(
                    schedule_id=s.id,
                    day_of_week=s.day_of_week,
                    start_time=s.start_time,
                    end_time=s.end_time
                ) for s in batch.schedules
            ]
            
            # Coaches
            coaches_list = []
            for assignment in batch.coach_assignments:
                if assignment.coach:
                    coaches_list.append(PreCreateCoach(
                        coach_id=assignment.coach.id,
                        coach_name=assignment.coach.user.full_name if assignment.coach.user else "Unknown"
                    ))
            
            # Students
            students_list = [
                PreCreateStudent(
                    student_id=s.id,
                    student_name=s.name,
                    age=s.age
                ) for s in batch.students
            ]
            
            pre_create_batches.append(PreCreateBatch(
                batch_id=batch.id,
                batch_name=batch.batch_name,
                school_id=batch.school_id,
                school_name=batch.school.name if batch.school else "",
                schedule=schedule_list,
                coaches=coaches_list,
                students=students_list
            ))
            
        return PreCreateResponse(batches=pre_create_batches)

    @staticmethod
    def get_admin_view_sessions(db: Session) -> PhysicalAssessmentSessionAdminViewResponse:
        sessions = PhysicalSessionRepository.get_all(db)
        view_sessions = []
        for session in sessions:
            coach_name = "Unknown"
            if session.coach_id:
                coach = CoachRepository.get_by_id(db, session.coach_id)
                if coach and coach.user:
                    coach_name = coach.user.full_name
            
            view_sessions.append(PhysicalAssessmentSessionAdminView(
                session_id=session.id,
                batch_id=session.batch_id,
                batch_name=session.batch.batch_name if session.batch else None,
                school_id=session.school_id,
                school_name=session.school.name if session.school else None,
                coach_id=session.coach_id,
                coach_name=coach_name,
                date_of_session=session.date_of_session,
                time_of_session=session.time_of_session
            ))
        return PhysicalAssessmentSessionAdminViewResponse(sessions=view_sessions)

    @staticmethod
    def get_coach_view_sessions(db: Session, coach_id: int) -> PhysicalAssessmentSessionAdminViewResponse:
        # Sessions created by coach OR sessions for batches assigned to coach
        
        # 1. Get batches assigned to coach
        assigned_batches_query = select(CoachBatch.batch_id).where(CoachBatch.coach_id == coach_id)
        assigned_batch_ids = db.scalars(assigned_batches_query).all()
        
        # 2. Query sessions
        query = select(PhysicalAssessmentSession).where(
            (PhysicalAssessmentSession.coach_id == coach_id) |
            (PhysicalAssessmentSession.batch_id.in_(assigned_batch_ids))
        )
        sessions = db.scalars(query).all()
        
        view_sessions = []
        for session in sessions:
            coach_name = "Unknown"
            if session.coach_id:
                coach = CoachRepository.get_by_id(db, session.coach_id)
                if coach and coach.user:
                    coach_name = coach.user.full_name
            
            view_sessions.append(PhysicalAssessmentSessionAdminView(
                session_id=session.id,
                batch_id=session.batch_id,
                batch_name=session.batch.batch_name if session.batch else None,
                school_id=session.school_id,
                school_name=session.school.name if session.school else None,
                coach_id=session.coach_id,
                coach_name=coach_name,
                date_of_session=session.date_of_session,
                time_of_session=session.time_of_session
            ))
        return PhysicalAssessmentSessionAdminViewResponse(sessions=view_sessions)
