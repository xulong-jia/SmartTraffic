from fastapi import APIRouter


router = APIRouter(prefix="/api/detections", tags=["detections"])


@router.get("")
def list_detections() -> dict[str, str]:
    return {"status": "not_implemented", "stage": "phase_1_contract_only"}
