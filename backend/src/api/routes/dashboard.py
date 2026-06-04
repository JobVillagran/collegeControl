from fastapi import APIRouter, Query

from src.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(refresh: bool = Query(default=False)):
    service = DashboardService()
    return service.get_dashboard(force_refresh=refresh)