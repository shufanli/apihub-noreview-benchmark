"""ApiHub FastAPI application."""
import os
from dotenv import load_dotenv

# Load env before other imports
env_path = os.path.join(os.path.dirname(__file__), "..", ".env.dev")
load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .seed import seed_data
from .routers import auth, keys, usage, billing, pricing

app = FastAPI(title="ApiHub", version="1.0.0")

# CORS
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(keys.router)
app.include_router(usage.router)
app.include_router(billing.router)
app.include_router(pricing.router)


@app.on_event("startup")
async def startup():
    init_db()
    seed_data()


@app.get("/api/health")
async def health():
    return {"status": "ok"}
