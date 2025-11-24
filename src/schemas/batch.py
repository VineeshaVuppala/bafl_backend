from datetime import datetime, time
from typing import List, Optional
import re

from pydantic import BaseModel, Field, field_validator, field_serializer


class BatchScheduleEntry(BaseModel):
    """Schedule payload without identifier."""

    day_of_week: str = Field(..., description="Day of the week, e.g., Monday")
    start_time: str = Field(..., description="Start time in 12-hour format (e.g., '04:00 PM')")
    end_time: str = Field(..., description="End time in 12-hour format (e.g., '05:00 PM')")

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        # Allow "HH:MM AM/PM" or "HH:MM" (24h fallback if user sends it, but prefer 12h)
        # Regex for 12-hour format: (0[1-9]|1[0-2]):[0-5][0-9] ?[AP]M
        match_12h = re.match(r"^(0?[1-9]|1[0-2]):([0-5][0-9]) ?([AP]M)$", v, re.IGNORECASE)
        if match_12h:
            return v.upper()
        
        # Fallback: check if it's already 24h format "HH:MM" or "HH:MM:SS"
        match_24h = re.match(r"^([01]?[0-9]|2[0-3]):([0-5][0-9])(:[0-5][0-9])?$", v)
        if match_24h:
            # Convert to 12h format for consistency? Or just allow it?
            # User asked for 12h format. Let's try to convert 24h to 12h if possible, or just accept valid time strings.
            # But for storage we need time object. Wait, schema is for API.
            # If I change type to str, I must ensure I can convert it to time object later.
            return v
            
        raise ValueError("Time must be in 12-hour format (e.g., '04:00 PM')")

    def to_time_obj(self, time_str: str) -> time:
        try:
            return datetime.strptime(time_str, "%I:%M %p").time()
        except ValueError:
            try:
                # Try 24h format
                return datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                 # Try 24h with seconds
                return datetime.strptime(time_str, "%H:%M:%S").time()


class BatchScheduleItem(BatchScheduleEntry):
    """Schedule entry including identifier."""

    schedule_id: int
    
    # Override fields to allow time objects from DB to be serialized to string
    start_time: str | time
    end_time: str | time

    @field_serializer("start_time", "end_time")
    def serialize_time(self, v: time | str, _info) -> str:
        if isinstance(v, time):
            return v.strftime("%I:%M %p")
        return str(v)



class BatchCreateRequest(BaseModel):
    """Contract request for batch creation."""

    school_id: int
    batch_name: str
    schedule: Optional[List[BatchScheduleEntry]] = None


class BatchCreateResponse(BaseModel):
    """Contract response for batch creation."""

    batch_id: int
    batch_name: str
    school_id: int
    school_name: str
    schedule: List[BatchScheduleItem] = Field(default_factory=list)


class BatchScheduleUpdateItem(BaseModel):
    """Item used when updating a batch schedule."""

    schedule_id: Optional[int] = Field(default=None, description="Existing schedule identifier, if updating")
    day_of_week: str
    start_time: str = Field(..., description="Start time in 12-hour format")
    end_time: str = Field(..., description="End time in 12-hour format")

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        # Reuse logic or duplicate it. Duplicating for simplicity as it's small.
        match_12h = re.match(r"^(0?[1-9]|1[0-2]):([0-5][0-9]) ?([AP]M)$", v, re.IGNORECASE)
        if match_12h:
            return v.upper()
        match_24h = re.match(r"^([01]?[0-9]|2[0-3]):([0-5][0-9])(:[0-5][0-9])?$", v)
        if match_24h:
            return v
        raise ValueError("Time must be in 12-hour format (e.g., '04:00 PM')")

    def to_time_obj(self, time_str: str) -> time:
        try:
            return datetime.strptime(time_str, "%I:%M %p").time()
        except ValueError:
            try:
                return datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                return datetime.strptime(time_str, "%H:%M:%S").time()


class BatchScheduleUpdateRequest(BaseModel):
    """Payload for updating a batch schedule."""

    schedule: List[BatchScheduleUpdateItem]


class BatchUpdateRequest(BaseModel):
    """Contract request for updating batch details and schedule."""

    batch_name: Optional[str] = None
    school_id: Optional[int] = None
    schedule: Optional[List[BatchScheduleUpdateItem]] = None


class BatchSummary(BaseModel):
    """Summary representation used in other contracts."""

    batch_id: int
    batch_name: str
    school_id: int
    school_name: str


class BatchDetail(BatchSummary):
    """Extended batch details including schedule information."""

    schedule: List[BatchScheduleItem] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None
