from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.repositories.school_repository import SchoolRepository
from src.db.repositories.coach_school_repository import CoachSchoolRepository
from src.db.repositories.coach_batch_repository import CoachBatchRepository
from src.db.models.school import School
from src.db.models.batch import Batch
from src.schemas.school import SchoolCreate, SchoolUpdate

class SchoolService:
    @staticmethod
    def create_school(db: Session, school_data: SchoolCreate) -> School:
        school = School(**school_data.model_dump())
        return SchoolRepository.create(db, school)

    @staticmethod
    def get_school(db: Session, school_id: int) -> School:
        return SchoolRepository.get_by_id(db, school_id)

    @staticmethod
    def get_all_schools(db: Session, skip: int = 0, limit: int = 100) -> list[School]:
        return SchoolRepository.get_all(db, skip, limit)

    @staticmethod
    def get_schools_for_coach(db: Session, coach_id: int, skip: int = 0, limit: int = 100) -> list[School]:
        school_map: dict[int, School] = {}
        school_ids: set[int] = set()

        coach_school_assignments = CoachSchoolRepository.get_schools_for_coach(db, coach_id)
        for assignment in coach_school_assignments:
            if assignment.school_id is None:
                continue
            school_ids.add(assignment.school_id)
            if assignment.school is not None:
                school_map[assignment.school_id] = assignment.school

        coach_batch_assignments = CoachBatchRepository.get_batches_for_coach(db, coach_id)
        batch_ids = [assignment.batch_id for assignment in coach_batch_assignments if assignment.batch_id]
        if batch_ids:
            batches = db.scalars(select(Batch).where(Batch.id.in_(batch_ids))).all()
            for batch in batches:
                if batch and batch.school_id:
                    school_ids.add(batch.school_id)
                    if batch.school is not None:
                        school_map[batch.school_id] = batch.school

        missing_school_ids = [school_id for school_id in school_ids if school_id not in school_map]
        if missing_school_ids:
            fetched_schools = SchoolRepository.get_by_ids(db, missing_school_ids)
            for school in fetched_schools:
                school_map[school.id] = school

        ordered_ids = sorted(
            school_ids,
            key=lambda school_id: school_map[school_id].name.lower() if school_id in school_map and school_map[school_id].name else "",
        )
        results = [school_map[school_id] for school_id in ordered_ids if school_id in school_map]

        if not results:
            return SchoolRepository.get_all(db, skip, limit)

        if skip:
            results = results[skip:]
        if limit is not None:
            results = results[:limit]
        return results

    @staticmethod
    def update_school(db: Session, school_id: int, school_data: SchoolUpdate) -> School:
        school = SchoolRepository.get_by_id(db, school_id)
        if not school:
            return None
        update_data_dict = school_data.model_dump(exclude_unset=True)
        return SchoolRepository.update(db, school, update_data_dict)

    @staticmethod
    def delete_school(db: Session, school_id: int) -> bool:
        school = SchoolRepository.get_by_id(db, school_id)
        if not school:
            return False
        SchoolRepository.delete(db, school)
        return True
