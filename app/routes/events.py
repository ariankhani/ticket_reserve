from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.events import Event
from app.schemas.events import EventCreate, EventOut, EventStatsOut
from app.services.bookings import get_event_stats

router = APIRouter(prefix="/event", tags=["events"])


@router.post("", response_model=EventOut)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    event = Event(title=payload.title, capacity=payload.capacity, booked_count=0)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}/stats", response_model=EventStatsOut)
def event_stats(event_id: int, db: Session = Depends(get_db)):
    stats = get_event_stats(db, event_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Event not found")
    return stats



