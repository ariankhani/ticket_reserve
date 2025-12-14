from datetime import datetime

from pydantic import BaseModel, Field


class BookRequest(BaseModel):
    user_id: int = Field(ge=1)
    event_id: int = Field(ge=1)


class BookingOut(BaseModel):
    id: int
    event_id: int
    user_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
