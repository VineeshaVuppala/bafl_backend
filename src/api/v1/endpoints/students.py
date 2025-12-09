from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.schemas.student import StudentCreate, StudentUpdate, StudentResponse, StudentChangeBatchRequest, StudentChangeBatchResponse, StudentBasicResponse
from src.services.student_service import StudentService
from src.db.models.student import Student as StudentModel
from src.db.models.batch import Batch as BatchModel
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from src.api.v1.dependencies.auth import get_current_user
from src.db.models.user import User, UserRole
from src.utils.input_parsing import parse_request
from pydantic import BaseModel

router = APIRouter(prefix="/students", tags=["Students"])

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED, openapi_extra={"requestBody": {"content": {"application/json": {"schema": StudentCreate.model_json_schema()}}, "required": True}})
async def create_student(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    student_data = await parse_request(request, StudentCreate)
    return StudentService.create_student(db, student_data)

@router.get("/", response_model=list[StudentResponse])
def get_students(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Load students with joined batch and school to populate school_name and batch_name without N+1 queries
    stmt = select(StudentModel).options(joinedload(StudentModel.batch).joinedload(BatchModel.school)).offset(skip).limit(limit)
    students = db.scalars(stmt).all()
    return students

@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = StudentService.get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@router.put("/{student_id}", response_model=StudentResponse, openapi_extra={"requestBody": {"content": {"application/json": {"schema": StudentUpdate.model_json_schema()}}, "required": True}})
async def update_student(
    student_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    student_data = await parse_request(request, StudentUpdate)
    student = StudentService.update_student(db, student_id, student_data)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    success = StudentService.delete_student(db, student_id)
    if not success:
        raise HTTPException(status_code=404, detail="Student not found")
    return None

@router.put("/{student_id}/change-batch", response_model=StudentChangeBatchResponse, openapi_extra={"requestBody": {"content": {"application/json": {"schema": StudentChangeBatchRequest.model_json_schema()}}, "required": True}})
async def change_student_batch(
    student_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    data = await parse_request(request, StudentChangeBatchRequest)
    result = StudentService.change_batch(db, student_id, data.new_batch_id)
    return result


@router.get("/by-filters", response_model=list[StudentBasicResponse])
def get_students_by_filters(
    school: str,
    batch: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    students = StudentService.get_students_by_school_and_batch(db, school, batch)
    return students
