from fastapi import APIRouter, Depends, Query

from src.security import verify_app_key
from src.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", dependencies=[Depends(verify_app_key)])
def get_dashboard(refresh: bool = Query(default=False)):
    service = DashboardService()
    return service.get_dashboard(force_refresh=refresh)