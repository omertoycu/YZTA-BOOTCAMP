import sentry_sdk
from fastapi import FastAPI

from app.api.routes import auth, leads, listings
from app.core.config import settings

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

app = FastAPI(title="PortföyAI API", version="0.1.0")

app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(leads.router)


@app.get("/health")
def health():
    return {"status": "ok"}
