"""Run the Stage 8EFG artifact-backed Evaluation MVP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "backend"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run SmartTraffic Stage 8EFG artifact-backed evaluation."
    )
    parser.add_argument("--run-id", required=True, help="Analysis run id to evaluate.")
    parser.add_argument("--dataset-id", help="Registered evaluation dataset id.")
    parser.add_argument(
        "--evaluation-type",
        default="event",
        choices=[
            "event",
            "flow_counting",
            "trajectory",
            "detection",
            "tracking",
            "regression",
        ],
        help="Evaluation metric family to run.",
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        help="Analysis results root. Defaults to backend settings.",
    )
    parser.add_argument(
        "--eval-root",
        type=Path,
        help="Evaluation artifact root. Defaults to evals/ or SMARTTRAFFIC_EVALS_DIR.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full response as JSON.",
    )
    args = parser.parse_args()

    from app.services.evaluation_service import EvaluationService

    service = EvaluationService(results_dir=args.results_root, eval_root=args.eval_root)
    response = service.run_evaluation(
        run_id=args.run_id,
        dataset_id=args.dataset_id,
        evaluation_type=args.evaluation_type,
    )
    if args.json:
        print(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True))
        return
    print(
        "Evaluation completed: "
        f"{response['evaluation_run']['evaluation_run_id']} "
        f"({response['evaluation_run']['evaluation_type']})"
    )
    print(f"Results: {len(response['results'])}")
    print(f"Failed cases: {len(response['failed_cases'])}")


if __name__ == "__main__":
    main()
