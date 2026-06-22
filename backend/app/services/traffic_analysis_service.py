from typing import Any


class TrafficAnalysisService:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}

    def register_run(
        self,
        run_id: str,
        video_id: str,
        result_dir: str,
        artifact_index: dict[str, Any],
    ) -> dict[str, Any]:
        run = {
            "id": run_id,
            "video_id": video_id,
            "status": "created",
            "result_dir": result_dir,
            "artifact_index": artifact_index,
        }
        self._runs[run_id] = run
        return dict(run)

    def list_runs(self) -> list[dict[str, Any]]:
        return list(self._runs.values())


traffic_analysis_service = TrafficAnalysisService()
