import time

from app.core.celery_config import celery_app
from app.database.db import SessionLocal
from app.services.bookings import finalize_booking


@celery_app.task(bind=True)
def finalize_booking_task(self, booking_id: int):
    """Finalize booking after 5 second delay (simulates PDF generation/email)."""
    # Simulate time-consuming ticket issuance process
    time.sleep(5)

    db = SessionLocal()
    try:
        finalize_booking(db, booking_id)
    finally:
        db.close()
