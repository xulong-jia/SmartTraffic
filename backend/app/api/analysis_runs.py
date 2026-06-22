from fastapi import APIRouter

from app.services.traffic_analysis_service import traffic_analysis_service


router = APIRouter(prefix="/api/analysis-runs", tags=["analysis-runs"])


@router.get("")
def list_analysis_runs() -> list[dict]:
    return traffic_analysis_service.list_runs()
