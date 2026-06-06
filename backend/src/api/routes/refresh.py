from fastapi import APIRouter, Depends

from src.security import verify_app_key
from src.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api", tags=["refresh"])


@router.post("/refresh", dependencies=[Depends(verify_app_key)])
def refresh_dashboard():
    service = DashboardService()
    return service.refresh_dashboard()