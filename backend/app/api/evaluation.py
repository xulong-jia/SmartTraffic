from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.analysis.evaluation_artifacts import EvaluationArtifactError
from app.db.session import get_db
from app.schemas.evaluation import (
    EvaluationDatasetCreate,
    EvaluationDatasetListResponse,
    EvaluationDatasetRecord,
    EvaluationResultListResponse,
    EvaluationResultRecord,
    EvaluationRunListResponse,
    EvaluationRunRecord,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationSummaryArtifact,
    FailedCaseListResponse,
    FailedCaseRecord,
)
from app.services.evaluation_service import (
    EvaluationDatasetNotFound,
    EvaluationService,
)


router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/datasets", response_model=EvaluationDatasetListResponse)
def list_evaluation_datasets(
    db: Session = Depends(get_db),
) -> EvaluationDatasetListResponse:
    try:
        return EvaluationDatasetListResponse(**EvaluationService(session=db).list_datasets())
    except EvaluationArtifactError as exc:
        raise _bad_request("invalid evaluation artifact") from exc


@router.post("/datasets", response_model=EvaluationDatasetRecord)
def register_evaluation_dataset(
    payload: EvaluationDatasetCreate,
    db: Session = Depends(get_db),
) -> EvaluationDatasetRecord:
    try:
        record = EvaluationService(session=db).register_dataset(payload.model_dump())
        db.commit()
        return EvaluationDatasetRecord(**record)
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    except EvaluationArtifactError as exc:
        raise _bad_request("invalid evaluation artifact") from exc


@router.get("/runs", response_model=EvaluationRunListResponse)
def list_evaluation_runs(
    run_id: str | None = Query(default=None),
    dataset_id: str | None = Query(default=None),
    evaluation_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> EvaluationRunListResponse:
    try:
        items = EvaluationService(session=db).list_evaluation_runs(
            run_id=run_id,
            dataset_id=dataset_id,
            evaluation_type=evaluation_type,
        )
        page_items = items[offset : offset + limit]
        return EvaluationRunListResponse(
            items=[EvaluationRunRecord(**item) for item in page_items],
            total=len(items),
            limit=limit,
            offset=offset,
        )
    except EvaluationArtifactError as exc:
        raise _bad_request("invalid evaluation artifact") from exc


@router.post("/run", response_model=EvaluationRunResponse)
def run_evaluation(
    payload: EvaluationRunRequest,
    db: Session = Depends(get_db),
) -> EvaluationRunResponse:
    try:
        response = EvaluationService(session=db).run_evaluation(
            run_id=payload.run_id,
            dataset_id=payload.dataset_id,
            evaluation_type=payload.evaluation_type,
            config=payload.config,
        )
        db.commit()
        return EvaluationRunResponse(**response)
    except EvaluationDatasetNotFound as exc:
        raise _not_found("evaluation dataset not found") from exc
    except KeyError as exc:
        raise _not_found("analysis run not found") from exc
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    except EvaluationArtifactError as exc:
        raise _bad_request("invalid evaluation artifact") from exc


@router.get("/results", response_model=EvaluationResultListResponse)
def list_evaluation_results(
    run_id: str | None = Query(default=None),
    evaluation_run_id: str | None = Query(default=None),
    evaluation_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> EvaluationResultListResponse:
    try:
        items = EvaluationService(session=db).list_results(
            run_id=run_id,
            evaluation_run_id=evaluation_run_id,
            evaluation_type=evaluation_type,
        )
        page_items = items[offset : offset + limit]
        return EvaluationResultListResponse(
            items=[EvaluationResultRecord(**item) for item in page_items],
            total=len(items),
            limit=limit,
            offset=offset,
        )
    except EvaluationArtifactError as exc:
        raise _bad_request("invalid evaluation artifact") from exc


@router.get("/summary/{run_id}", response_model=EvaluationSummaryArtifact)
def get_evaluation_summary(
    run_id: str,
    db: Session = Depends(get_db),
) -> EvaluationSummaryArtifact:
    try:
        return EvaluationSummaryArtifact(
            **EvaluationService(session=db).get_evaluation_summary(run_id)
        )
    except KeyError as exc:
        raise _not_found("analysis run not found") from exc
    except EvaluationArtifactError as exc:
        raise _bad_request("invalid evaluation artifact") from exc


@router.get("/failed-cases", response_model=FailedCaseListResponse)
def list_failed_cases(
    run_id: str | None = Query(default=None),
    evaluation_run_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> FailedCaseListResponse:
    try:
        items = EvaluationService(session=db).list_failed_cases(
            run_id=run_id,
            evaluation_run_id=evaluation_run_id,
        )
        page_items = items[offset : offset + limit]
        return FailedCaseListResponse(
            items=[FailedCaseRecord(**item) for item in page_items],
            total=len(items),
            limit=limit,
            offset=offset,
        )
    except EvaluationArtifactError as exc:
        raise _bad_request("invalid evaluation artifact") from exc


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
