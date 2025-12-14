"""
Test booking service functions.
"""
import pytest
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session

from app.models.books import Booking, BookingStatus
from app.models.events import Event
from app.services.bookings import (
    SoldOutError,
    create_booking,
    finalize_booking,
    get_event_stats,
    get_overall_report,
)


class TestBookingService:
    """Test booking service functions."""

    def test_create_booking_success(self, db_session: Session, redis_client):
        """Test creating a booking successfully."""
        event = Event(title="Available Event", capacity=10, booked_count=0)
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        booking = create_booking(db_session, event_id=event.id, user_id=1)

        assert booking.id is not None
        assert booking.event_id == event.id
        assert booking.user_id == 1
        assert booking.status == BookingStatus.PENDING.value

        # Verify booked_count was incremented
        db_session.refresh(event)
        assert event.booked_count == 1

    def test_create_booking_sold_out(self, db_session: Session, redis_client):
        """Test booking when event is sold out."""
        event = Event(title="Sold Out Event", capacity=1, booked_count=1)
        db_session.add(event)
        db_session.commit()

        with pytest.raises(SoldOutError, match="Event is sold out"):
            create_booking(db_session, event_id=event.id, user_id=2)

    def test_create_booking_last_ticket(self, db_session: Session, redis_client):
        """Test booking the last available ticket."""
        event = Event(title="Almost Full Event", capacity=5, booked_count=4)
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        booking = create_booking(db_session, event_id=event.id, user_id=10)

        assert booking is not None
        db_session.refresh(event)
        assert event.booked_count == 5

        # Next booking should fail
        with pytest.raises(SoldOutError):
            create_booking(db_session, event_id=event.id, user_id=11)

    def test_create_booking_race_condition_prevention(self, db_session: Session, redis_client):
        """Test that Redis lock prevents race conditions."""
        event = Event(title="Race Event", capacity=1, booked_count=0)
        db_session.add(event)
        db_session.commit()
        event_id = event.id

        results = []
        errors = []

        def attempt_booking(user_id: int):
            try:
                booking = create_booking(db_session, event_id=event_id, user_id=user_id)
                results.append(booking)
            except SoldOutError as e:
                errors.append(str(e))
            except Exception as e:
                errors.append(f"Unexpected error: {e}")

        # Simulate concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(attempt_booking, i) for i in range(1, 6)]
            for f in futures:
                f.result()

        # Only 1 booking should succeed
        assert len(results) == 1
        assert len(errors) == 4

        # Verify event state
        db_session.refresh(event)
        assert event.booked_count == 1

    def test_finalize_booking(self, db_session: Session):
        """Test finalizing a booking."""
        event = Event(title="Event to Finalize", capacity=10, booked_count=1)
        db_session.add(event)
        db_session.commit()

        booking = Booking(
            event_id=event.id,
            user_id=5,
            status=BookingStatus.PENDING.value
        )
        db_session.add(booking)
        db_session.commit()
        db_session.refresh(booking)

        # Finalize the booking
        finalize_booking(db_session, booking.id)

        db_session.refresh(booking)
        assert booking.status == BookingStatus.FINALIZED.value

    def test_finalize_nonexistent_booking(self, db_session: Session):
        """Test finalizing a booking that doesn't exist."""
        # Should not raise an error
        finalize_booking(db_session, 99999)

    def test_get_event_stats(self, db_session: Session):
        """Test getting event statistics."""
        event = Event(title="Stats Event", capacity=20, booked_count=10)
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        # Create some bookings
        for i in range(10):
            status = BookingStatus.FINALIZED.value if i < 5 else BookingStatus.PENDING.value
            booking = Booking(event_id=event.id, user_id=i + 1, status=status)
            db_session.add(booking)
        db_session.commit()

        stats = get_event_stats(db_session, event.id)

        assert stats["event_id"] == event.id
        assert stats["capacity"] == 20
        assert stats["booked_count"] == 10
        assert stats["finalized_count"] == 5

    def test_get_event_stats_nonexistent(self, db_session: Session):
        """Test getting stats for nonexistent event."""
        stats = get_event_stats(db_session, 99999)
        assert stats == {}

    def test_get_overall_report(self, db_session: Session):
        """Test getting overall report across all events."""
        # Create multiple events
        event1 = Event(title="Event 1", capacity=50, booked_count=30)
        event2 = Event(title="Event 2", capacity=100, booked_count=80)
        event3 = Event(title="Event 3", capacity=20, booked_count=15)
        
        db_session.add_all([event1, event2, event3])
        db_session.commit()

        # Create bookings
        for event in [event1, event2, event3]:
            db_session.refresh(event)
            for i in range(5):
                booking = Booking(
                    event_id=event.id,
                    user_id=i + 100,
                    status=BookingStatus.FINALIZED.value
                )
                db_session.add(booking)
        db_session.commit()

        report = get_overall_report(db_session)

        assert report["total_capacity"] == 170  # 50 + 100 + 20
        assert report["total_reserved"] == 125  # 30 + 80 + 15
        assert report["total_finalized"] == 15  # 5 * 3

    def test_get_overall_report_empty_database(self, db_session: Session):
        """Test overall report with no events."""
        report = get_overall_report(db_session)

        assert report["total_capacity"] == 0 or report["total_capacity"] is None
        assert report["total_reserved"] == 0 or report["total_reserved"] is None
        assert report["total_finalized"] == 0

    def test_multiple_users_booking_same_event(self, db_session: Session, redis_client):
        """Test multiple users booking tickets for the same event."""
        event = Event(title="Popular Event", capacity=5, booked_count=0)
        db_session.add(event)
        db_session.commit()
        event_id = event.id

        bookings = []
        for user_id in range(1, 6):
            booking = create_booking(db_session, event_id=event_id, user_id=user_id)
            bookings.append(booking)

        assert len(bookings) == 5
        
        db_session.refresh(event)
        assert event.booked_count == 5

        # 6th booking should fail
        with pytest.raises(SoldOutError):
            create_booking(db_session, event_id=event_id, user_id=6)
