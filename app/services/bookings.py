
import redis
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.redis_sonfig import get_redis_url
from app.models.books import Booking, BookingStatus
from app.models.events import Event


class SoldOutError(Exception):
    pass


def get_redis_client():
    """Get Redis client for locking."""
    return redis.from_url(get_redis_url(), decode_responses=True)


def create_booking(db: Session, *, event_id: int, user_id: int) -> Booking:
    """
    Create a booking with Redis Lock to prevent race conditions.
    This ensures only one request can book the last ticket.
    """
    redis_client = get_redis_client()
    lock_key = f"event_lock:{event_id}"
    lock = redis_client.lock(lock_key, timeout=10, blocking_timeout=5)

    try:
        # Acquire the lock - only one process can proceed at a time
        if not lock.acquire(blocking=True, blocking_timeout=5):
            raise SoldOutError("Could not acquire lock, please try again.")

        try:
            # Check if we're already in a transaction (for tests)
            if db.in_transaction():
                # Use the existing transaction
                return _create_booking_in_transaction(db, event_id, user_id)
            else:
                # Start a new transaction
                with db.begin():
                    return _create_booking_in_transaction(db, event_id, user_id)
        finally:
            # Always release the lock
            lock.release()
    except redis.exceptions.LockError: # type: ignore
        raise SoldOutError("Could not acquire lock, please try again.")


def _create_booking_in_transaction(db: Session, event_id: int, user_id: int) -> Booking:
    """Internal function to create booking within a transaction."""
    # Check capacity and increment booked_count atomically
    stmt = (
        update(Event)
        .where(Event.id == event_id)
        .where(Event.booked_count < Event.capacity)
        .values(booked_count=Event.booked_count + 1)
    )
    res = db.execute(stmt)
    if res.rowcount != 1:  # type: ignore
        raise SoldOutError("Event is sold out.")

    booking = Booking(
        event_id=event_id,
        user_id=user_id,
        status=BookingStatus.PENDING.value,
    )
    db.add(booking)
    db.flush()  # gets booking.id
    db.refresh(booking)
    return booking


def finalize_booking(db: Session, booking_id: int) -> None:
    if db.in_transaction():
        # Use existing transaction and commit it
        _finalize_booking_in_transaction(db, booking_id)
        db.commit()  # Commit the transaction
    else:
        # Start new transaction
        with db.begin():
            _finalize_booking_in_transaction(db, booking_id)


def _finalize_booking_in_transaction(db: Session, booking_id: int) -> None:
    """Internal function to finalize booking within a transaction."""
    booking = db.get(Booking, booking_id)
    if not booking:
        return
    booking.status = BookingStatus.FINALIZED.value


def get_event_stats(db: Session, event_id: int) -> dict:
    event = db.get(Event, event_id)
    if not event:
        return {}

    finalized_count = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.event_id == event_id,
            Booking.status == BookingStatus.FINALIZED.value,
        )
    )

    return {
        "event_id": event.id,
        "capacity": event.capacity,
        "booked_count": event.booked_count,
        "finalized_count": int(finalized_count or 0),
    }


def get_overall_report(db: Session) -> dict:
    """Return aggregated totals across all events."""
    total_capacity = db.scalar(select(func.sum(Event.capacity)))
    total_reserved = db.scalar(select(func.sum(Event.booked_count)))

    total_finalized = db.scalar(
        select(func.count(Booking.id)).where(Booking.status == BookingStatus.FINALIZED.value)
    )

    return {
        "total_capacity": int(total_capacity or 0),
        "total_reserved": int(total_reserved or 0),
        "total_finalized": int(total_finalized or 0),
    }
