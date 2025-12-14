# Ticket Fast API

Simple ticket booking service (FastAPI) with background tasks and Redis locking.

This repository implements a minimal ticket booking system exposing a HTTP API, a background Celery task to finalize bookings, and a locking mechanism (Redis) to protect against race conditions when multiple clients try to book the last tickets concurrently. The test-suite exercises the API, service layer, Celery tasks, Redis locking, and race conditions.

**What's included**
- **API**: FastAPI application exposing endpoints to create events, create bookings, and view reports.
- **Database**: SQLAlchemy (SQLite by default) models for `Event` and `Booking`.
- **Locking**: Redis-based locks (used when creating bookings to avoid overselling).
- **Background work**: Celery tasks for finalizing bookings (simulates PDF/email issuance).
- **Tests**: A complete pytest test-suite covering models, services, Redis behavior, Celery tasks, API endpoints and a race-condition integration test.

**Important:** This README only documents running the project and tests using Docker (the repository contains helpful Docker configurations and a dedicated Docker test flow).

**Quick links**
- **Code**: `app/` directory contains the application modules and tests under `app/tests/`.

**Prerequisites**
- Docker and Docker Compose (modern `docker compose` command).

**Run the application (Docker-only)**

1. Build and start the application services (this will start the FastAPI app, Redis and any other configured services):

```bash
docker compose up --build -d
```

2. Check logs for the app service:

```bash
docker compose logs -f
```

3. Stop and remove the containers, networks and volumes created by Compose:

```bash
docker compose down
```

Notes:
- The FastAPI app is configured in `app/main.py` and served by the container built from the repository. API is available at http://localhost:8000 by default when running locally with the included compose config.
- The compose stacks in this repository include an additional `docker-compose.test.yml` used specifically for running the test-suite inside a containerized environment.

**Run tests (Docker)**

This project includes a `Makefile` with convenient test targets. The `make test-docker` target launches a throwaway container that installs test dependencies and runs pytest inside Docker, isolating test runs from your host environment.

From the repository root run:

```bash
make test-docker
```

What `make test-docker` does:
- Builds the `ticket_fast_api-test` image (uses `Dockerfile.test`), then runs `pytest` against `app/tests/` inside the container.
- It also starts a temporary Redis service (via `docker-compose.test.yml`) so Redis-backed tests run against a real Redis instance.
- The command is configured to abort on the first failing test container and to propagate the test exit code.

If you prefer to run the entire test-suite directly with `docker compose` (same effect):

```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test
```

Useful `Makefile` targets
- **`make test`**: run pytest locally (non-Docker). Useful for quick runs inside a dev environment.
- **`make test-docker`**: run the test-suite inside Docker (recommended for CI or when you don't want to install test deps locally).
- **`make clean-test`**: remove test artifacts such as `test_ticket.db` and pytest cache.

Troubleshooting
- If `docker compose up` hangs or fails due to port conflicts, ensure nothing else is listening on port 8000.
- If Docker containers fail to start due to missing permissions when installing Python packages, run Docker commands as a user with appropriate privileges or configure a non-root build stage (the provided Dockerfiles install packages as root inside the container, which is normal).
- For Redis-specific tests we use `fakeredis` mocks in unit tests and a real Redis instance when using `docker-compose.test.yml`.

CI Suggestions
- Use `make test-docker` inside your CI job to run the full, hermetic test-suite. That ensures Redis and other services are started exactly as in local testing.

Want me to also add a short `docker compose` snippet tailored for production or add healthchecks? Reply and I'll add it.
