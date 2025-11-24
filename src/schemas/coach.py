from typing import List, Optional

from pydantic import BaseModel


class CoachCreateRequest(BaseModel):
    name: str
    username: str
    password: str
    schools: Optional[List[int]] = None
    batches: Optional[List[int]] = None


class CoachUpdateRequest(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    schools: Optional[List[int]] = None
    batches: Optional[List[int]] = None


class CoachSchoolAssignment(BaseModel):
    school_id: int
    school_name: str


class CoachBatchAssignment(BaseModel):
    batch_id: int
    batch_name: str
    school_id: int
    school_name: str


class CoachContractDetails(BaseModel):
    coach_id: int
    name: str
    schools: List[CoachSchoolAssignment]
    batches: List[CoachBatchAssignment]


class CoachCreateResponse(BaseModel):
    message: str
    coach: CoachContractDetails


class CoachUpdateResponse(BaseModel):
    message: str
    coach: CoachContractDetails
