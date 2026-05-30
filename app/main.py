from fastapi import FastAPI
from app.routers import auth, places, sessions

app = FastAPI(title="Worker Tracking API")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(places.router, prefix="/places", tags=["places"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])

@app.get("/")
def root():
    return {"status": "ok"}