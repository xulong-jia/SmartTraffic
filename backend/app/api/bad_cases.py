from fastapi import APIRouter


router = APIRouter(prefix="/api/bad-cases", tags=["bad-cases"])


@router.get("")
def list_bad_cases() -> dict[str, str]:
    return {"status": "not_implemented", "stage": "phase_1_placeholder"}
