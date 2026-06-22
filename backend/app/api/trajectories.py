from fastapi import APIRouter


router = APIRouter(prefix="/api/trajectories", tags=["trajectories"])


@router.get("")
def list_trajectories() -> dict[str, str]:
    return {"status": "not_implemented", "stage": "phase_1_contract_only"}
