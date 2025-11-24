from __future__ import annotations

from typing import Iterable, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.db.models.batch import Batch
from src.db.models.batch_schedule import BatchSchedule
from src.db.models.school import School
from src.db.repositories.batch_repository import BatchRepository
from src.db.repositories.school_repository import SchoolRepository
from src.schemas.batch import (
    BatchCreateRequest,
    BatchCreateResponse,
    BatchDetail,
    BatchScheduleEntry,
    BatchScheduleItem,
    BatchScheduleUpdateItem,
    BatchUpdateRequest,
)


class BatchService:
    """Business logic for batch resources with contract-aware scheduling."""

    @staticmethod
    def _ensure_school(db: Session, school_id: int) -> School:
        school = SchoolRepository.get_by_id(db, school_id)
        if not school:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")
        return school

    @staticmethod
    def _to_schedule_item(schedule: BatchSchedule) -> BatchScheduleItem:
        return BatchScheduleItem(
            schedule_id=schedule.id,
            day_of_week=schedule.day_of_week,
            start_time=schedule.start_time.strftime("%I:%M %p"),
            end_time=schedule.end_time.strftime("%I:%M %p"),
        )

    @staticmethod
    def _build_batch_detail(batch: Batch) -> BatchDetail:
        school = batch.school
        schedule_items = [BatchService._to_schedule_item(item) for item in batch.schedules]
        return BatchDetail(
            batch_id=batch.id,
            batch_name=batch.batch_name,
            school_id=batch.school_id,
            school_name=school.name if school else "",
            schedule=schedule_items,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
        )

    @staticmethod
    def _create_schedule_entries(db: Session, batch_id: int, entries: Iterable[BatchScheduleEntry]) -> None:
        new_items: List[BatchSchedule] = []
        for entry in entries:
            schedule = BatchSchedule(
                batch_id=batch_id,
                day_of_week=entry.day_of_week,
                start_time=entry.to_time_obj(entry.start_time),
                end_time=entry.to_time_obj(entry.end_time),
            )
            db.add(schedule)
            new_items.append(schedule)
        if new_items:
            db.flush()

    @staticmethod
    def _sync_schedule(db: Session, batch: Batch, items: List[BatchScheduleUpdateItem]) -> None:
        existing = {schedule.id: schedule for schedule in list(batch.schedules)}
        keep_ids: set[int] = set()
        new_items: List[BatchSchedule] = []

        for item in items:
            if item.schedule_id is not None:
                schedule = existing.get(item.schedule_id)
                if not schedule:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Schedule entry {item.schedule_id} not found for batch",
                    )
                schedule.day_of_week = item.day_of_week
                schedule.start_time = item.to_time_obj(item.start_time)
                schedule.end_time = item.to_time_obj(item.end_time)
                keep_ids.add(schedule.id)
            else:
                schedule = BatchSchedule(
                    batch_id=batch.id,
                    day_of_week=item.day_of_week,
                    start_time=item.to_time_obj(item.start_time),
                    end_time=item.to_time_obj(item.end_time),
                )
                db.add(schedule)
                new_items.append(schedule)

        if new_items:
            db.flush()
            keep_ids.update(schedule.id for schedule in new_items)

        for schedule_id, schedule in existing.items():
            if schedule_id not in keep_ids:
                db.delete(schedule)

        db.flush()
        db.expire(batch, ["schedules"])

    @staticmethod
    def create_batch(db: Session, payload: BatchCreateRequest) -> BatchCreateResponse:
        school = BatchService._ensure_school(db, payload.school_id)

        try:
            batch = Batch(school_id=school.id, batch_name=payload.batch_name)
            db.add(batch)
            db.flush()

            if payload.schedule:
                BatchService._create_schedule_entries(db, batch.id, payload.schedule)
            
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(batch)
        schedule_items = [BatchService._to_schedule_item(item) for item in batch.schedules]

        return BatchCreateResponse(
            batch_id=batch.id,
            batch_name=batch.batch_name,
            school_id=school.id,
            school_name=school.name,
            schedule=schedule_items,
        )

    @staticmethod
    def get_batch(db: Session, batch_id: int) -> BatchDetail:
        batch = BatchRepository.get_by_id(db, batch_id)
        if not batch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
        return BatchService._build_batch_detail(batch)

    @staticmethod
    def get_all_batches(db: Session, skip: int = 0, limit: int = 100) -> List[BatchDetail]:
        batches = BatchRepository.get_all(db, skip, limit)
        return [BatchService._build_batch_detail(batch) for batch in batches]

    @staticmethod
    def update_batch(db: Session, batch_id: int, payload: BatchUpdateRequest) -> BatchDetail:
        batch = BatchRepository.get_by_id(db, batch_id)
        if not batch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

        update_fields: dict[str, object] = {}
        school = batch.school

        if payload.batch_name is not None:
            update_fields["batch_name"] = payload.batch_name

        if payload.school_id is not None and payload.school_id != batch.school_id:
            school = BatchService._ensure_school(db, payload.school_id)
            update_fields["school_id"] = school.id

        with db.begin():
            for field, value in update_fields.items():
                setattr(batch, field, value)

            if payload.schedule is not None:
                BatchService._sync_schedule(db, batch, payload.schedule)

        db.refresh(batch)
        if school is None:
            school = batch.school
        return BatchService._build_batch_detail(batch)

    @staticmethod
    def delete_batch(db: Session, batch_id: int) -> None:
        batch = BatchRepository.get_by_id(db, batch_id)
        if not batch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
        with db.begin():
            db.delete(batch)
