from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .routers import prices, refuels, trips, auth, fahrer, routen_vorlagen, sondereffekte

app = FastAPI(title="Spritpreis-Advisor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prices.router)
app.include_router(refuels.router)
app.include_router(trips.router)
app.include_router(auth.router)
app.include_router(fahrer.router)
app.include_router(routen_vorlagen.router)
app.include_router(sondereffekte.router)


@app.on_event("startup")
def on_startup():
    init_db()


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
UPLOADS_DIR = Path(settings.db_path).resolve().parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
