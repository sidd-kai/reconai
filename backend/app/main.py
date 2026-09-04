from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from dotenv import load_dotenv


load_dotenv(
    dotenv_path=Path(__file__).resolve().parents[2] / ".env",
    override=False,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from backend.app.api.routes.agent import (
    router as agent_router,
)

from backend.app.api.routes.audit import (
    router as audit_router,
)

from backend.app.api.routes.dashboard import (
    router as dashboard_router,
)

from backend.app.api.routes.razorpay_demo import (
    router as razorpay_demo_router,
)

from backend.app.api.routes.razorpay_webhooks import (
    router as razorpay_webhook_router,
)


app = FastAPI(
    title="ReconAI",
    version="0.1.0",
    description=(
        "Deterministic AI Finance Controller "
        "for multi-source reconciliation."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "OPTIONS",
    ],
    allow_headers=[
        "*",
    ],
)


app.include_router(
    dashboard_router
)

app.include_router(
    agent_router
)

app.include_router(
    audit_router
)

app.include_router(
    razorpay_demo_router
)

app.include_router(
    razorpay_webhook_router
)


@app.get(
    "/health"
)
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "reconai",
    }
