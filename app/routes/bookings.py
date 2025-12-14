from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.books import BookingOut, BookRequest
from app.services.bookings import SoldOutError, create_booking
from app.tasks import finalize_booking_task

router = APIRouter(prefix="/book", tags=["bookings"])


@router.post("", response_model=BookingOut)
def book_ticket(payload: BookRequest, db: Session = Depends(get_db)):
    try:
        booking = create_booking(db, event_id=payload.event_id, user_id=payload.user_id)
    except SoldOutError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # enqueue durable background work to finalize the booking
    import contextlib
    with contextlib.suppress(Exception):
        delay_fn = getattr(finalize_booking_task, "delay", None)
        if callable(delay_fn):
            delay_fn(booking.id)
        else:
            finalize_booking_task(booking.id) # type: ignore

    return booking
