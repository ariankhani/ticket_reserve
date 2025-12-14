
from pydantic import BaseModel, Field


# ---------- Event ----------
class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    capacity: int = Field(ge=1)


class EventOut(BaseModel):
    id: int
    title: str
    capacity: int
    booked_count: int

    class Config:
        from_attributes = True


class EventStatsOut(BaseModel):
    event_id: int
    capacity: int
    booked_count: int
    finalized_count: int
