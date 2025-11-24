from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.v1.dependencies.auth import get_current_user
from src.db.database import get_db
from src.db.models.user import User, UserRole
from src.schemas.batch import (
    BatchCreateRequest,
    BatchCreateResponse,
    BatchDetail,
    BatchUpdateRequest,
)
from src.services.batch_service import BatchService

router = APIRouter(prefix="/batches", tags=["Batches"])

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

@router.post("/", response_model=BatchCreateResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: BatchCreateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> BatchCreateResponse:
    return BatchService.create_batch(db, payload)

@router.get("/", response_model=list[BatchDetail])
def get_batches(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return BatchService.get_all_batches(db, skip, limit)

@router.get("/{batch_id}", response_model=BatchDetail)
def get_batch(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return BatchService.get_batch(db, batch_id)

@router.put("/{batch_id}", response_model=BatchDetail)
def update_batch(
    batch_id: int,
    payload: BatchUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return BatchService.update_batch(db, batch_id, payload)

@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(
    batch_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    BatchService.delete_batch(db, batch_id)
    return None
