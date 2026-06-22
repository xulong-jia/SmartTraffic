from fastapi import APIRouter


router = APIRouter(prefix="/api/zones", tags=["zones"])


@router.get("")
def list_zones() -> dict[str, str]:
    return {"status": "not_implemented", "stage": "phase_1_contract_only"}
