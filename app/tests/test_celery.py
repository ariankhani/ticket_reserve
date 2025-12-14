"""
Test Celery tasks.
"""
import time
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.books import Booking, BookingStatus
from app.models.events import Event
from app.tasks import finalize_booking_task
from app.tests.conftest import TestingSessionLocal


class TestCeleryTasks:
    """Test Celery task functionality."""

    def test_finalize_booking_task_updates_status(self, db_session: Session):
        """Test that finalize_booking_task updates booking status."""
        # Create event and booking
        event = Event(title="Test Event", capacity=10, booked_count=1)
        db_session.add(event)
        db_session.commit()

        booking = Booking(
            event_id=event.id,
            user_id=1,
            status=BookingStatus.PENDING.value
        )
        db_session.add(booking)
        db_session.commit()
        db_session.refresh(booking)

        booking_id = booking.id

        # Mock SessionLocal to return a fresh session from the test sessionmaker
        with patch('app.tasks.SessionLocal', return_value=TestingSessionLocal()):
            # Call the task function directly (not through Celery)
            finalize_booking_task.run(booking_id)  # Use .run() method

        # The finalize_booking function commits, so we need to refresh from DB
        db_session.refresh(booking)
        assert booking.status == BookingStatus.FINALIZED.value

    def test_finalize_booking_task_with_nonexistent_booking(self, db_session: Session):
        """Test that finalize_booking_task handles nonexistent bookings gracefully."""
        with patch('app.tasks.SessionLocal', return_value=TestingSessionLocal()):
            # Should not raise an exception
            finalize_booking_task.run(99999)

    def test_finalize_booking_task_delay_simulation(self, db_session: Session):
        """Test that the task simulates a time delay."""
        event = Event(title="Delayed Event", capacity=5, booked_count=1)
        db_session.add(event)
        db_session.commit()

        booking = Booking(
            event_id=event.id,
            user_id=2,
            status=BookingStatus.PENDING.value
        )
        db_session.add(booking)
        db_session.commit()
        
        booking_id = booking.id
        
        # Measure time taken
        start_time = time.time()

        with patch('app.tasks.SessionLocal', return_value=TestingSessionLocal()):
            finalize_booking_task.run(booking_id)
        
        elapsed_time = time.time() - start_time
        
        # Should take at least 5 seconds (simulated processing time)
        assert elapsed_time >= 5.0
        
        # Verify booking was finalized
        db_session.refresh(booking)
        assert booking.status == BookingStatus.FINALIZED.value

    def test_celery_app_configuration(self):
        """Test that Celery app is properly configured."""
        from app.core.celery_config import celery_app
        
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content
        assert celery_app.conf.task_track_started is True

    def test_finalize_booking_task_is_registered(self):
        """Test that the finalize_booking task is registered with Celery."""
        from app.core.celery_config import celery_app
        
        # Check if task is registered
        task_name = "app.tasks.finalize_booking_task"
        assert task_name in celery_app.tasks or "finalize_booking_task" in str(celery_app.tasks)

    def test_multiple_bookings_finalization(self, db_session: Session):
        """Test finalizing multiple bookings."""
        event = Event(title="Multi Booking Event", capacity=10, booked_count=3)
        db_session.add(event)
        db_session.commit()

        bookings = []
        for i in range(3):
            booking = Booking(
                event_id=event.id,
                user_id=i + 1,
                status=BookingStatus.PENDING.value
            )
            db_session.add(booking)
            bookings.append(booking)
        
        db_session.commit()
        
        # Finalize all bookings
        with patch('app.tasks.SessionLocal', return_value=TestingSessionLocal()):
            for booking in bookings:
                db_session.refresh(booking)
                finalize_booking_task.run(booking.id)
        
        # Verify all are finalized
        for booking in bookings:
            db_session.refresh(booking)
            assert booking.status == BookingStatus.FINALIZED.value
