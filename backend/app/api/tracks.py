from fastapi import APIRouter


router = APIRouter(prefix="/api/tracks", tags=["tracks"])


@router.get("")
def list_tracks() -> dict[str, str]:
    return {"status": "not_implemented", "stage": "phase_1_contract_only"}
