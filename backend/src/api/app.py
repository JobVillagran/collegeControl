from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import FRONTEND_ORIGINS
from src.api.routes.dashboard import router as dashboard_router
from src.api.routes.health import router as health_router
from src.api.routes.refresh import router as refresh_router

app = FastAPI(title="College Control API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(refresh_router)