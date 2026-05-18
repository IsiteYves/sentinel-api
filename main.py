import os

from dotenv import load_dotenv

load_dotenv()  # loads .env before any other module reads env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.evidence import router as evidence_router
from routers.report import router as report_router

app = FastAPI(
    title="Sentinel API",
    description="Forensic-grade cyber-harassment evidence preservation for Kenya.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,https://sentinel-saver.vercel.app",
)
_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(evidence_router)
app.include_router(report_router)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "service": "sentinel-api"}
