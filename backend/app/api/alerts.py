from fastapi import APIRouter


router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
def list_alerts() -> dict[str, str]:
    return {"status": "not_implemented", "stage": "phase_1_contract_only"}
