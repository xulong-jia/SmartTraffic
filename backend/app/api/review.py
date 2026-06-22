from fastapi import APIRouter


router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/events")
def list_review_events() -> dict[str, str]:
    return {"status": "not_implemented", "stage": "phase_1_placeholder"}
