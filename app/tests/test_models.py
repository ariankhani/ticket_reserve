"""
Test database models (Event and Booking).
"""
import pytest
from sqlalchemy.orm import Session

from app.models.books import Booking, BookingStatus
from app.models.events import Event


class TestEventModel:
    """Test the Event model."""

    def test_create_event(self, db_session: Session):
        """Test creating an event."""
        event = Event(title="Test Event", capacity=100, booked_count=0)
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        assert event.id is not None
        assert event.title == "Test Event"
        assert event.capacity == 100
        assert event.booked_count == 0

    def test_event_relationship_with_bookings(self, db_session: Session):
        """Test the relationship between Event and Booking."""
        event = Event(title="Concert", capacity=50, booked_count=0)
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        booking1 = Booking(event_id=event.id, user_id=1, status=BookingStatus.PENDING.value)
        booking2 = Booking(event_id=event.id, user_id=2, status=BookingStatus.PENDING.value)
        db_session.add(booking1)
        db_session.add(booking2)
        db_session.commit()

        # Refresh to load relationships
        db_session.refresh(event)
        
        assert len(event.bookings) == 2
        assert all(b.event_id == event.id for b in event.bookings)

    def test_update_booked_count(self, db_session: Session):
        """Test updating booked_count."""
        event = Event(title="Workshop", capacity=10, booked_count=0)
        db_session.add(event)
        db_session.commit()

        event.booked_count = 5
        db_session.commit()
        db_session.refresh(event)

        assert event.booked_count == 5


class TestBookingModel:
    """Test the Booking model."""

    def test_create_booking(self, db_session: Session):
        """Test creating a booking."""
        event = Event(title="Festival", capacity=200, booked_count=0)
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        booking = Booking(
            event_id=event.id,
            user_id=42,
            status=BookingStatus.PENDING.value
        )
        db_session.add(booking)
        db_session.commit()
        db_session.refresh(booking)

        assert booking.id is not None
        assert booking.event_id == event.id
        assert booking.user_id == 42
        assert booking.status == BookingStatus.PENDING.value
        assert booking.created_at is not None

    def test_booking_status_transition(self, db_session: Session):
        """Test transitioning booking status from PENDING to FINALIZED."""
        event = Event(title="Seminar", capacity=30, booked_count=0)
        db_session.add(event)
        db_session.commit()

        booking = Booking(
            event_id=event.id,
            user_id=99,
            status=BookingStatus.PENDING.value
        )
        db_session.add(booking)
        db_session.commit()

        # Change status to FINALIZED
        booking.status = BookingStatus.FINALIZED.value
        db_session.commit()
        db_session.refresh(booking)

        assert booking.status == BookingStatus.FINALIZED.value

    def test_booking_relationship_with_event(self, db_session: Session):
        """Test the relationship from Booking to Event."""
        event = Event(title="Conference", capacity=500, booked_count=0)
        db_session.add(event)
        db_session.commit()

        booking = Booking(
            event_id=event.id,
            user_id=10,
            status=BookingStatus.PENDING.value
        )
        db_session.add(booking)
        db_session.commit()
        db_session.refresh(booking)

        assert booking.event.title == "Conference"
        assert booking.event.capacity == 500
