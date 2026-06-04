from fastapi import APIRouter

from src.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api", tags=["refresh"])


@router.post("/refresh")
def refresh_dashboard():
    service = DashboardService()
    return service.refresh_dashboard()