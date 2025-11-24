from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.v1.dependencies.auth import get_current_user
from src.db.database import get_db
from src.db.models.user import User, UserRole
from src.schemas.school import SchoolCreate, SchoolCreateResponse, SchoolResponse, SchoolUpdate
from src.services.school_service import SchoolService

router = APIRouter(prefix="/schools", tags=["Schools"])

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

@router.post("/", response_model=SchoolCreateResponse, status_code=status.HTTP_201_CREATED)
def create_school(
    payload: SchoolCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SchoolCreateResponse:
    school = SchoolService.create_school(db, payload)
    return SchoolCreateResponse(school_id=school.id, school_name=school.name)

@router.get("/", response_model=list[SchoolResponse])
def get_schools(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return SchoolService.get_all_schools(db, skip, limit)

@router.get("/{school_id}", response_model=SchoolResponse)
def get_school(
    school_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    school = SchoolService.get_school(db, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school

@router.put("/{school_id}", response_model=SchoolResponse)
def update_school(
    school_id: int,
    payload: SchoolUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    school = SchoolService.update_school(db, school_id, payload)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school

@router.delete("/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_school(
    school_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    success = SchoolService.delete_school(db, school_id)
    if not success:
        raise HTTPException(status_code=404, detail="School not found")
    return None
