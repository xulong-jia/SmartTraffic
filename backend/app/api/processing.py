from fastapi import APIRouter

from app.services.processing_service import processing_service


router = APIRouter(prefix="/api/processing", tags=["processing"])


@router.get("/tasks")
def list_processing_tasks() -> list[dict]:
    return processing_service.list_tasks()
