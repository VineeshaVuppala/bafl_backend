from sqlalchemy.orm import Session
from src.db.repositories.school_repository import SchoolRepository
from src.db.models.school import School
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
