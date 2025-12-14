from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.db import Base, engine
from app.routes import bookings, events, reports

app = FastAPI()

# Configure CORS
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create all tables (in production, use migrations such as Alembic)
Base.metadata.create_all(bind=engine)

# Include the routers
app.include_router(events.router)
app.include_router(bookings.router)
app.include_router(reports.router)
