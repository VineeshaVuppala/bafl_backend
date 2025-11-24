from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.v1.dependencies.auth import get_current_user
from src.db.database import get_db
from src.db.models.user import User, UserRole
from src.schemas.coach import (
    CoachContractDetails,
    CoachCreateRequest,
    CoachCreateResponse,
    CoachUpdateRequest,
    CoachUpdateResponse,
)
from src.services.coach_service import CoachService

router = APIRouter(prefix="/coaches", tags=["Coaches"])

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

@router.post("/", response_model=CoachCreateResponse, status_code=status.HTTP_201_CREATED)
def create_coach(
    payload: CoachCreateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CoachCreateResponse:
    details = CoachService.create_coach(db, payload)
    return CoachCreateResponse(message="Coach created successfully", coach=details)

@router.get("/", response_model=list[CoachContractDetails])
def get_coaches(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return CoachService.list_coaches(db, skip, limit)

@router.get("/{coach_id}", response_model=CoachContractDetails)
def get_coach(
    coach_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return CoachService.get_coach(db, coach_id)

@router.put("/{coach_id}", response_model=CoachUpdateResponse)
def update_coach(
    coach_id: int,
    payload: CoachUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CoachUpdateResponse:
    details = CoachService.update_coach(db, coach_id, payload)
    return CoachUpdateResponse(message="Coach updated successfully", coach=details)

@router.delete("/{coach_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coach(
    coach_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    CoachService.delete_coach(db, coach_id)
    return None
