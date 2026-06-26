from fastapi import APIRouter, HTTPException, Query, status

from app.analysis.bad_case_artifacts import BadCaseArtifactError
from app.schemas.bad_case import (
    BadCaseCreateApiRequest,
    BadCaseDetailResponse,
    BadCaseFromFailedCaseRequest,
    BadCaseFromReviewRequest,
    BadCaseListResponse,
    BadCaseRecord,
    BadCaseSummary,
    BadCaseUpdateApiRequest,
)
from app.services.bad_case_service import BadCaseService, FailedCaseNotFound


router = APIRouter(prefix="/api/bad-cases", tags=["bad-cases"])


@router.get("", response_model=BadCaseListResponse)
def list_bad_cases(
    run_id: str | None = Query(default=None),
    case_type: str | None = Query(default=None),
    module: str | None = Query(default=None),
    case_status: str | None = Query(default=None, alias="status"),
    tag: str | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=1000),
    offset: int = Query(default=0, ge=0),
) -> BadCaseListResponse:
    try:
        service = BadCaseService()
        items = service.list_bad_cases(
            run_id=run_id,
            case_type=case_type,
            module=module,
            status=case_status,
            tag=tag,
        )
        page_items = items[offset : offset + limit]
        return BadCaseListResponse(
            items=[BadCaseRecord(**item) for item in page_items],
            total=len(items),
            limit=limit,
            offset=offset,
            summary=BadCaseSummary(**_summary_for_items(items)),
        )
    except KeyError as exc:
        raise _not_found("analysis run not found") from exc
    except BadCaseArtifactError as exc:
        raise _bad_request("invalid bad case artifact") from exc


@router.get("/summary", response_model=BadCaseSummary)
def summarize_bad_cases(
    run_id: str | None = Query(default=None),
) -> BadCaseSummary:
    try:
        return BadCaseSummary(**BadCaseService().summarize_bad_cases(run_id=run_id))
    except KeyError as exc:
        raise _not_found("analysis run not found") from exc
    except BadCaseArtifactError as exc:
        raise _bad_request("invalid bad case artifact") from exc


@router.post("/from-review", response_model=BadCaseDetailResponse)
def create_bad_case_from_review(
    payload: BadCaseFromReviewRequest,
) -> BadCaseDetailResponse:
    service = BadCaseService()
    try:
        record = service.create_bad_case_from_review(
            run_id=payload.run_id,
            review_id=payload.review_id,
            event_id=payload.event_id,
            case_type=payload.case_type,
            module=payload.module,
            description=payload.description,
            expected_result=payload.expected_result,
            actual_result=payload.actual_result,
            tags=payload.tags,
        )
        if payload.root_cause:
            record = service.update_bad_case(
                run_id=payload.run_id,
                case_id=record["case_id"],
                updates={"root_cause": payload.root_cause},
            )
        return BadCaseDetailResponse(**record)
    except KeyError as exc:
        detail = (
            "analysis run not found"
            if not service.run_exists(payload.run_id)
            else "review not found"
        )
        raise _not_found(detail) from exc
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    except BadCaseArtifactError as exc:
        raise _bad_request("invalid bad case artifact") from exc


@router.post("/from-failed-case", response_model=BadCaseDetailResponse)
def create_bad_case_from_failed_case(
    payload: BadCaseFromFailedCaseRequest,
) -> BadCaseDetailResponse:
    service = BadCaseService()
    try:
        record = service.create_bad_case_from_failed_case(
            run_id=payload.run_id,
            failed_case_id=payload.failed_case_id,
            case_type=payload.case_type,
            module=payload.module,
            description=payload.description,
            expected_result=payload.expected_result,
            actual_result=payload.actual_result,
            root_cause=payload.root_cause,
            tags=payload.tags,
        )
        return BadCaseDetailResponse(**record)
    except FailedCaseNotFound as exc:
        raise _not_found("failed case not found") from exc
    except KeyError as exc:
        raise _not_found("analysis run not found") from exc
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    except BadCaseArtifactError as exc:
        raise _bad_request("invalid bad case artifact") from exc


@router.get("/{case_id}", response_model=BadCaseDetailResponse)
def get_bad_case(
    case_id: str,
    run_id: str | None = Query(default=None),
) -> BadCaseDetailResponse:
    try:
        service = BadCaseService()
        record = (
            service.get_bad_case(run_id=run_id, case_id=case_id)
            if run_id
            else service.find_bad_case(case_id=case_id)
        )
        return BadCaseDetailResponse(**record)
    except KeyError as exc:
        detail = "analysis run not found" if run_id and not service.run_exists(run_id) else "bad case not found"
        raise _not_found(detail) from exc
    except BadCaseArtifactError as exc:
        raise _bad_request("invalid bad case artifact") from exc


@router.post("", response_model=BadCaseDetailResponse)
def create_bad_case(payload: BadCaseCreateApiRequest) -> BadCaseDetailResponse:
    try:
        record = BadCaseService().create_bad_case(
            run_id=payload.run_id,
            record=payload.model_dump(exclude={"run_id"}),
        )
        return BadCaseDetailResponse(**record)
    except KeyError as exc:
        raise _not_found("analysis run not found") from exc
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    except BadCaseArtifactError as exc:
        raise _bad_request("invalid bad case artifact") from exc


@router.patch("/{case_id}", response_model=BadCaseDetailResponse)
def update_bad_case(
    case_id: str,
    payload: BadCaseUpdateApiRequest,
) -> BadCaseDetailResponse:
    service = BadCaseService()
    try:
        run_id = payload.run_id
        if run_id is None:
            run_id = service.find_bad_case(case_id=case_id)["run_id"]
        updates = payload.model_dump(exclude={"run_id"}, exclude_none=True)
        record = service.update_bad_case(
            run_id=run_id,
            case_id=case_id,
            updates=updates,
        )
        return BadCaseDetailResponse(**record)
    except KeyError as exc:
        detail = (
            "analysis run not found"
            if payload.run_id and not service.run_exists(payload.run_id)
            else "bad case not found"
        )
        raise _not_found(detail) from exc
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc
    except BadCaseArtifactError as exc:
        raise _bad_request("invalid bad case artifact") from exc


def _summary_for_items(items: list[dict]) -> dict:
    from app.analysis.bad_case_artifacts import summarize_bad_case_records

    return summarize_bad_case_records(items)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
