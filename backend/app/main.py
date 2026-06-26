from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    alerts,
    analysis_runs,
    bad_cases,
    cameras,
    detections,
    event_rules,
    evaluation,
    events,
    health,
    processing,
    realtime,
    reports,
    review,
    tracks,
    trajectories,
    videos,
    zones,
)
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.project_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(cameras.router)
    app.include_router(videos.router)
    app.include_router(processing.router)
    app.include_router(detections.router)
    app.include_router(tracks.router)
    app.include_router(trajectories.router)
    app.include_router(events.router)
    app.include_router(event_rules.router)
    app.include_router(alerts.router)
    app.include_router(zones.router)
    app.include_router(analysis_runs.router)
    app.include_router(review.router)
    app.include_router(bad_cases.router)
    app.include_router(evaluation.router)
    app.include_router(reports.router)
    app.include_router(realtime.router)
    return app


app = create_app()
