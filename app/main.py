from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    auth, places, sessions,
    manager_workers, manager_sessions, manager_sessions_history,
    manager_places, manager_dashboard
)

app = FastAPI(title="Worker Tracking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(places.router, prefix="/places", tags=["places"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(manager_workers.router, prefix="/manager/workers", tags=["manager-workers"])
app.include_router(manager_sessions.router, prefix="/manager/sessions", tags=["manager-sessions"])
app.include_router(manager_sessions_history.router, prefix="/manager/sessions-history", tags=["manager-sessions-history"])
app.include_router(manager_places.router, prefix="/manager/places", tags=["manager-places"])
app.include_router(manager_dashboard.router, prefix="/manager/dashboard", tags=["manager-dashboard"])


@app.get("/")
def root():
    return {"status": "ok"}