"""
Test script to verify race condition handling for ticket booking.

This script:
1. Creates an event with capacity=1
2. Sends 10 concurrent booking requests
3. Verifies only 1 booking succeeds
4. Checks that capacity never goes negative
5. Waits for background finalization and verifies final status
"""

import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def create_event(client: TestClient, title: str, capacity: int) -> dict:
    """Create an event and return the event data."""
    response = client.post(
        "/event",
        json={"title": title, "capacity": capacity},
    )
    response.raise_for_status()
    return response.json()


def book_ticket(client: TestClient, user_id: int, event_id: int) -> tuple[int, dict | None]:
    """Try to book a ticket. Returns (status_code, response_data or None)."""
    try:
        response = client.post(
            "/book",
            json={"user_id": user_id, "event_id": event_id},
        )
        if response.status_code == 200:
            return (response.status_code, response.json())
        return (response.status_code, None)
    except Exception as e:
        print(f"  User {user_id} error: {e}")
        return (500, None)


def get_event_stats(client: TestClient, event_id: int) -> dict:
    """Get event statistics."""
    response = client.get(f"/event/{event_id}/stats")
    response.raise_for_status()
    return response.json()


def test_race_condition(client: TestClient, db_session: Session, redis_client):
    """Main test function."""
    print("=" * 70)
    print("RACE CONDITION TEST - Ticket Booking System")
    print("=" * 70)

    # Step 1: Create event with capacity=1
    print("\n[1] Creating event with capacity=1...")
    event = create_event(client, title="Race Test Event", capacity=1)
    event_id = event["id"]
    print(f"    ✓ Event created: ID={event_id}, capacity={event['capacity']}")

    # Step 2: Send 10 concurrent requests
    print("\n[2] Sending 10 concurrent booking requests...")
    num_requests = 10

    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        # Submit all booking requests concurrently
        futures = [
            executor.submit(book_ticket, client, user_id, event_id)
            for user_id in range(1, num_requests + 1)
        ]

        # Collect results
        results = [f.result() for f in futures]

    # Step 3: Analyze results
    print("\n[3] Analyzing results...")
    successful = [r for r in results if r[0] == 200]
    failed = [r for r in results if r[0] != 200]

    print(f"    Successful bookings: {len(successful)}")
    print(f"    Failed bookings: {len(failed)}")

    if successful:
        for status, data in successful:
            if data:
                print(f"      ✓ Booking ID={data['id']}, User={data['user_id']}, Status={data['status']}")

    # Step 4: Verify capacity
    print("\n[4] Checking event stats immediately after booking...")
    stats = get_event_stats(client, event_id)
    print(f"    Total capacity: {stats['capacity']}")
    print(f"    Booked count: {stats['booked_count']}")
    print(f"    Finalized count: {stats['finalized_count']}")

    # Verify race condition prevention
    assert len(successful) == 1, f"Expected 1 successful booking, got {len(successful)}"
    assert len(failed) == 9, f"Expected 9 failed bookings, got {len(failed)}"
    assert stats['booked_count'] == 1, f"Expected booked_count=1, got {stats['booked_count']}"
    assert stats['capacity'] == 1, f"Expected capacity=1, got {stats['capacity']}"

    print("\n[5] ✓ Race condition test passed!")
    print("    - Only 1 booking succeeded out of 10 concurrent requests")
    print("    - Event capacity respected")
    print("    - No overselling occurred")

    # Step 5: Assertions
    print("\n[5] Verifying correctness...")
    assert len(successful) == 1, f"❌ FAILED: Expected 1 success, got {len(successful)}"
    print("    ✓ Only 1 booking succeeded (as expected)")

    assert stats['booked_count'] == 1, f"❌ FAILED: Expected booked_count=1, got {stats['booked_count']}"
    print("    ✓ Booked count is correct (1)")

    assert stats['booked_count'] <= stats['capacity'], "❌ FAILED: Capacity went negative!"
    print("    ✓ Capacity is never negative")

    # Step 6: Manually finalize the booking (since Celery isn't running in tests)
    print("\n[6] Manually finalizing booking (simulating Celery task)...")
    from app.services.bookings import finalize_booking
    
    # Get the booking that was created
    from app.models.books import Booking
    
    booking = db_session.query(Booking).filter(Booking.event_id == event_id).first()
    if booking:
        finalize_booking(db_session, booking.id)
        print(f"    ✓ Finalized booking ID={booking.id}")
    else:
        print("    ❌ No booking found to finalize")

    # Check final stats
    stats_after = get_event_stats(client, event_id)
    print(f"    Final capacity: {stats_after['capacity']}")
    print(f"    Final booked count: {stats_after['booked_count']}")
    print(f"    Final finalized count: {stats_after['finalized_count']}")
    
    # Verify finalization worked
    assert stats_after['finalized_count'] == 1, f"❌ FAILED: Expected finalized_count=1, got {stats_after['finalized_count']}"
    
    print("\n[7] ✓ Complete race condition test passed!")
    print("    - Only 1 booking succeeded out of 10 concurrent requests")
    print("    - Event capacity respected")
    print("    - Manual finalization worked")
    print("    - No overselling occurred")


if __name__ == "__main__":
    try:
        test_race_condition()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
