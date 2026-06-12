from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import engine, Base
from backend.models import *  # noqa: F401, F403 - ensure all models are imported for table creation
from backend.routers import auth, users, accounts, resources, topology, certificates, cloudwatch, sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _init_admin()
    from backend.scheduler.scheduler import start_scheduler
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


def _init_admin():
    from backend.database import SessionLocal
    from backend.models.user import User
    from backend.core.security import hash_password
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.is_admin == True).first():
            admin = User(
                username="admin",
                email="admin@local.dev",
                hashed_password=hash_password("admin123"),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


app = FastAPI(title="AWS Multi-Account Ops Platform", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(resources.router)
app.include_router(topology.router)
app.include_router(certificates.router)
app.include_router(cloudwatch.router)
app.include_router(sync.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
