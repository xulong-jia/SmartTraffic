from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.analysis.export import REPORT_EXPORT_HEADERS, report_filename
from app.db.session import get_db
from app.services.report_service import ReportService


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/runs")
def list_report_runs(
    limit: int = Query(default=100, ge=0, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return ReportService(db).list_runs(limit=limit, offset=offset)


@router.get("/{run_id}/summary")
def get_report_summary(run_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        return ReportService(db).build_summary(run_id)
    except KeyError as exc:
        raise _not_found(f"analysis run not found: {exc.args[0]}") from exc


@router.get("/{run_id}/export.json")
def export_report_json(run_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        return ReportService(db).build_json_report(run_id)
    except KeyError as exc:
        raise _not_found(f"analysis run not found: {exc.args[0]}") from exc


@router.get("/{run_id}/export.csv")
def export_report_csv(
    run_id: str,
    section: str = Query(default="events"),
    db: Session = Depends(get_db),
) -> Response:
    if section not in REPORT_EXPORT_HEADERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unsupported report section",
        )
    try:
        payload = ReportService(db).build_csv(run_id, section)
    except KeyError as exc:
        raise _not_found(f"analysis run not found: {exc.args[0]}") from exc
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{report_filename(run_id, section, "csv")}"'
        )
    }
    return Response(content=payload, media_type="text/csv", headers=headers)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
