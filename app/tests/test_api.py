"""
Test API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.books import Booking, BookingStatus
from app.models.events import Event


class TestEventEndpoints:
    """Test event-related API endpoints."""

    def test_create_event(self, client: TestClient):
        """Test creating an event via API."""
        response = client.post(
            "/event",
            json={"title": "API Test Event", "capacity": 100}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "API Test Event"
        assert data["capacity"] == 100
        assert data["booked_count"] == 0
        assert "id" in data

    def test_create_event_validation(self, client: TestClient):
        """Test event creation with invalid data."""
        response = client.post(
            "/event",
            json={"title": "Test"}  # Missing capacity
        )
        
        assert response.status_code == 422  # Validation error

    def test_get_event_stats(self, client: TestClient, db_session: Session):
        """Test getting event statistics via API."""
        # Create event directly in database
        event = Event(title="Stats Test", capacity=50, booked_count=20)
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        # Create some finalized bookings
        for i in range(10):
            booking = Booking(
                event_id=event.id,
                user_id=i + 1,
                status=BookingStatus.FINALIZED.value
            )
            db_session.add(booking)
        db_session.commit()

        response = client.get(f"/event/{event.id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == event.id
        assert data["capacity"] == 50
        assert data["booked_count"] == 20
        assert data["finalized_count"] == 10

    def test_get_event_stats_not_found(self, client: TestClient):
        """Test getting stats for nonexistent event."""
        response = client.get("/event/99999/stats")
        assert response.status_code == 404


class TestBookingEndpoints:
    """Test booking-related API endpoints."""

    def test_book_ticket_success(self, client: TestClient, db_session: Session, redis_client):
        """Test booking a ticket via API."""
        # Create event
        event = Event(title="Bookable Event", capacity=10, booked_count=0)
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        response = client.post(
            "/book",
            json={"event_id": event.id, "user_id": 42}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == event.id
        assert data["user_id"] == 42
        assert data["status"] == BookingStatus.PENDING.value
        assert "id" in data

    def test_book_ticket_sold_out(self, client: TestClient, db_session: Session, redis_client):
        """Test booking when event is sold out."""
        event = Event(title="Full Event", capacity=1, booked_count=1)
        db_session.add(event)
        db_session.commit()

        response = client.post(
            "/book",
            json={"event_id": event.id, "user_id": 99}
        )

        assert response.status_code == 409  # Conflict
        assert "sold out" in response.json()["detail"].lower()

    def test_book_ticket_validation(self, client: TestClient):
        """Test booking with invalid data."""
        response = client.post(
            "/book",
            json={"event_id": 1}  # Missing user_id
        )
        
        assert response.status_code == 422

    def test_multiple_bookings_same_event(self, client: TestClient, db_session: Session, redis_client):
        """Test multiple users booking the same event."""
        event = Event(title="Multi User Event", capacity=5, booked_count=0)
        db_session.add(event)
        db_session.commit()
        event_id = event.id

        successful_bookings = []
        for user_id in range(1, 6):
            response = client.post(
                "/book",
                json={"event_id": event_id, "user_id": user_id}
            )
            assert response.status_code == 200
            successful_bookings.append(response.json())

        assert len(successful_bookings) == 5

        # 6th booking should fail
        response = client.post(
            "/book",
            json={"event_id": event_id, "user_id": 6}
        )
        assert response.status_code == 409


class TestReportEndpoints:
    """Test report-related API endpoints."""

    def test_overall_report(self, client: TestClient, db_session: Session):
        """Test getting overall report via API."""
        # Create events
        event1 = Event(title="Event A", capacity=100, booked_count=50)
        event2 = Event(title="Event B", capacity=200, booked_count=150)
        db_session.add_all([event1, event2])
        db_session.commit()

        # Create some finalized bookings
        for event in [event1, event2]:
            db_session.refresh(event)
            for i in range(5):
                booking = Booking(
                    event_id=event.id,
                    user_id=i + 100,
                    status=BookingStatus.FINALIZED.value
                )
                db_session.add(booking)
        db_session.commit()

        response = client.get("/report")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_capacity"] == 300
        assert data["total_reserved"] == 200
        assert data["total_finalized"] == 10

    def test_overall_report_empty(self, client: TestClient):
        """Test overall report with no events."""
        response = client.get("/report")
        
        assert response.status_code == 200
        data = response.json()
        # Should handle empty database gracefully

    def test_event_report(self, client: TestClient, db_session: Session):
        """Test getting event-specific report."""
        event = Event(title="Report Event", capacity=75, booked_count=40)
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        # Add finalized bookings
        for i in range(15):
            booking = Booking(
                event_id=event.id,
                user_id=i + 500,
                status=BookingStatus.FINALIZED.value
            )
            db_session.add(booking)
        db_session.commit()

        response = client.get(f"/report/event/{event.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == event.id
        assert data["capacity"] == 75
        assert data["booked_count"] == 40
        assert data["finalized_count"] == 15

    def test_event_report_not_found(self, client: TestClient):
        """Test event report for nonexistent event."""
        response = client.get("/report/event/99999")
        assert response.status_code == 404


class TestAPIIntegration:
    """Test complete API workflows."""

    def test_complete_booking_workflow(self, client: TestClient, redis_client):
        """Test complete workflow: create event -> book ticket -> check stats."""
        # 1. Create event
        response = client.post(
            "/event",
            json={"title": "Workflow Event", "capacity": 10}
        )
        assert response.status_code == 200
        event_id = response.json()["id"]

        # 2. Book tickets
        for user_id in range(1, 4):
            response = client.post(
                "/book",
                json={"event_id": event_id, "user_id": user_id}
            )
            assert response.status_code == 200

        # 3. Check event stats
        response = client.get(f"/event/{event_id}/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["booked_count"] == 3
        assert stats["capacity"] == 10

        # 4. Check overall report
        response = client.get("/report")
        assert response.status_code == 200
        report = response.json()
        assert report["total_reserved"] == 3

    def test_concurrent_api_bookings(self, client: TestClient, db_session: Session, redis_client):
        """Test concurrent API requests don't cause race conditions."""
        from concurrent.futures import ThreadPoolExecutor

        # Create event
        event = Event(title="Concurrent Event", capacity=3, booked_count=0)
        db_session.add(event)
        db_session.commit()
        event_id = event.id

        results = []

        def book_via_api(user_id: int):
            response = client.post(
                "/book",
                json={"event_id": event_id, "user_id": user_id}
            )
            return response.status_code

        # Try to book 10 tickets for event with capacity 3
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(book_via_api, i) for i in range(1, 11)]
            results = [f.result() for f in futures]

        # Count successful bookings (status 200)
        successful = [r for r in results if r == 200]
        failed = [r for r in results if r == 409]

        # Exactly 3 should succeed
        assert len(successful) == 3
        assert len(failed) == 7
