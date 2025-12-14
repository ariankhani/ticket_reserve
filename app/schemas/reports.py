from pydantic import BaseModel


class ReportOut(BaseModel):
    total_capacity: int
    total_reserved: int
    total_finalized: int

    class Config:
        from_attributes = True
