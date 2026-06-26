"""Run SmartTraffic Evaluation workflows, including Stage 4E regression replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "backend"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run SmartTraffic evaluation workflows, including Stage 4E regression replay."
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
        "--database-url",
        help="SQLAlchemy database URL used with --write-db.",
    )
    parser.add_argument(
        "--write-db",
        dest="write_db",
        action="store_true",
        help="Also persist evaluation dataset/result records to the database.",
    )
    parser.add_argument(
        "--no-write-db",
        dest="write_db",
        action="store_false",
        help="Do not write evaluation records to the database.",
    )
    parser.set_defaults(write_db=False)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full response as JSON.",
    )
    parser.add_argument("--case-type", help="Regression bad case type filter.")
    parser.add_argument("--module", help="Regression bad case module filter.")
    parser.add_argument("--status", help="Regression bad case status filter.")
    parser.add_argument("--tag", help="Regression bad case tag filter.")
    parser.add_argument(
        "--apply-updates",
        action="store_true",
        help="For regression only, update Bad Case statuses from replay results.",
    )
    args = parser.parse_args()

    from app.services.evaluation_service import EvaluationService

    config = {
        key: value
        for key, value in {
            "case_type": args.case_type,
            "module": args.module,
            "status": args.status,
            "tag": args.tag,
            "apply_updates": args.apply_updates,
        }.items()
        if value not in (None, False)
    }

    if args.write_db:
        from app.db.session import get_sessionmaker

        session_factory = get_sessionmaker(database_url=args.database_url)
        with session_factory() as session:
            service = EvaluationService(
                results_dir=args.results_root,
                eval_root=args.eval_root,
                session=session,
            )
            response = service.run_evaluation(
                run_id=args.run_id,
                dataset_id=args.dataset_id,
                evaluation_type=args.evaluation_type,
                config=config,
            )
            session.commit()
    else:
        service = EvaluationService(results_dir=args.results_root, eval_root=args.eval_root)
        response = service.run_evaluation(
            run_id=args.run_id,
            dataset_id=args.dataset_id,
            evaluation_type=args.evaluation_type,
            config=config,
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
    regression = response.get("summary", {}).get("summary", {}).get("bad_case_regression")
    if isinstance(regression, dict):
        print(
            "Bad Case regression: "
            f"status={regression.get('status')} "
            f"total={regression.get('total_cases')} "
            f"open={regression.get('open_cases')} "
            f"fixed={regression.get('fixed_cases')} "
            f"verified={regression.get('verified_cases')} "
            f"pass_rate={regression.get('regression_pass_rate')}"
        )


if __name__ == "__main__":
    main()
