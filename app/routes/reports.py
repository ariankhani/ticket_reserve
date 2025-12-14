from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.events import EventStatsOut
from app.schemas.reports import ReportOut
from app.services.bookings import get_event_stats, get_overall_report

router = APIRouter(prefix="/report", tags=["reports"])


@router.get("", response_model=ReportOut)
def overall_report(db: Session = Depends(get_db)):
    """Aggregate report across all events."""
    return get_overall_report(db)


@router.get("/event/{event_id}", response_model=EventStatsOut)
def event_report(event_id: int, db: Session = Depends(get_db)):
    stats = get_event_stats(db, event_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Event not found")
    return stats
