# 🎟 Ticket FastAPI

A minimal, concurrency-safe ticket booking service built with **FastAPI**, **SQLite**, **Redis locking**, and **Celery background tasks**.

This project demonstrates how to correctly handle **race conditions** (multiple users booking the last available ticket at the same time) while keeping the API responsive using asynchronous background processing.

---

## ✨ Features

- **FastAPI REST API**
  - Create events
  - Book tickets
  - View event statistics
- **Database**
  - SQLAlchemy models (`Event`, `Booking`)
  - SQLite by default (simple and portable)
- **Concurrency protection**
  - Redis-based locks to prevent over-booking
  - Atomic database updates
- **Background processing**
  - Celery task to finalize bookings (simulates PDF/email issuance)
- **Test coverage**
  - API endpoints
  - Service layer
  - Redis locking behavior
  - Celery tasks
  - Race-condition integration tests

---

## 📂 Project Structure

```
app/
├── main.py            # FastAPI application entrypoint
├── models.py          # SQLAlchemy models
├── schemas.py         # Pydantic schemas
├── services/          # Business logic
├── tasks/             # Celery tasks
└── tests/             # Pytest test-suite
```

---

## 🧰 Prerequisites

- Docker
- Docker Compose (`docker compose`)

No local Python or Redis installation is required.

---

## ▶ Run the Application (Docker)

```bash
docker compose up --build -d
```

API URL: http://localhost:8000  
Swagger UI: http://localhost:8000/docs

---

## 🧪 Run Tests (Docker)

```bash
make test-docker
```

---

## 🔐 Concurrency Model

- Redis lock per event
- Atomic capacity update
- Guaranteed no over-booking

⚠️ SQLite is for demo/testing. Use PostgreSQL in production.

---

## 🧠 Background Tasks

Booking API responds immediately (200 OK)

Finalization (PDF/email simulation) happens asynchronously via Celery

Booking status transitions: PENDING → FINALIZED

## 🧩 CI Recommendation

Use:

make test-docker

This guarantees:

Real Redis

Identical environment locally and in CI

No dependency leaks from host machine

📌 Notes

Redis is required for locking (included in Docker setup)

Fakeredis is used in unit tests

Real Redis is used in integration tests


