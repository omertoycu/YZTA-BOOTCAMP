import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, billing, internal, leads, listings, offices, reports, webhooks
from app.core.config import settings

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

app = FastAPI(title="PortföyAI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(offices.router)
app.include_router(listings.router)
app.include_router(leads.router)
app.include_router(reports.router)
app.include_router(webhooks.router)
app.include_router(internal.router)
app.include_router(billing.router)


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    # HTTPException'lar (401/404/vb.) zaten FastAPI'nin kendi handler'ından
    # geçer; bu sadece beklenmeyen hatalar için tutarlı bir JSON gövdesi sağlar
    # (varsayılan davranış düz metin "Internal Server Error" döner).
    return JSONResponse(status_code=500, content={"detail": "Beklenmeyen bir hata oluştu"})


@app.get("/health")
def health():
    return {"status": "ok"}
