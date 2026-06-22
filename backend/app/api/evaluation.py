from fastapi import APIRouter


router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/results")
def list_evaluation_results() -> dict[str, str]:
    return {"status": "not_implemented", "stage": "phase_1_placeholder"}
