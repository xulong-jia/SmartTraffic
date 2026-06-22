from fastapi import APIRouter


router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
def list_events() -> dict[str, str]:
    return {"status": "not_implemented", "stage": "phase_1_contract_only"}
