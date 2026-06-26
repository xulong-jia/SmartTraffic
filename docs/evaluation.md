# Evaluation Center

本文档记录 Stage 8HI 后的 Evaluation Center artifact-backed MVP，以及 Full
Stage 3EF 后的 Evaluation DB workflow。它仍不代表工业级检测 / 跟踪评测体系
已经完成。

## 当前状态

Stage 8EFG / Stage 8HI 已实现：

- `evals/datasets/evaluation_datasets.json` 数据集注册表。
- `evals/results/evaluation_runs.jsonl` 评测运行记录。
- `evals/results/evaluation_results.jsonl` 指标结果记录。
- `evals/results/failed_cases.jsonl` Evaluation failed cases。
- `results/traffic_analysis/{run_id}/evaluation_summary.json` run-level summary。
- Evaluation API、CLI 和 Evaluation Center 前端 MVP。
- `POST /api/bad-cases/from-failed-case` failed case -> Bad Case MVP。
- Bad Case regression summary MVP。

Full Stage 3EF 已实现：

- `evaluation_datasets` DB-backed dataset registry。
- `evaluation_results` DB-backed result persistence。
- failed cases 持久化在 `evaluation_results.summary["failed_cases"]` 中；没有新增
  failed_cases 独立表。
- Evaluation API DB-first 查询，DB 缺失时 fallback 到 artifacts。
- `scripts/run_evals.py --write-db --database-url ...` 可选写入 DB，同时保留
  artifact 输出。
- failed cases 可通过 `POST /api/bad-cases/from-failed-case` 转为 DB Bad Case，
  同一 `run_id + failed_case_id` 幂等。

当前仍未实现：

- 真实 rerun-based Bad Case regression pipeline。
- 工业级 mAP、IDF1、MOTA。
- 权限、多用户、实时流或生产部署。

## Artifacts

Evaluation artifacts 位于 `evals/`，真实 generated results 不应提交到 Git。
仓库可以保留 `.gitkeep` 和 Stage 9CD 小型 toy expected files；`evals/results/`
仍只保留 `.gitkeep`，真实 evaluation run/result/failed-case artifacts 不提交。

```text
evals/
  datasets/
    evaluation_datasets.json
  expected/
  results/
    evaluation_runs.jsonl
    evaluation_results.jsonl
    failed_cases.jsonl
```

每次评测还会在对应 analysis run 目录写入：

```text
results/traffic_analysis/{run_id}/evaluation_summary.json
```

该文件会同步刷新 `metadata.json`、`manifest.json` 和 `artifact_index.json`
中的 `evaluation_summary` 状态，但不会覆盖 detection、tracking、trajectory、
event、alert、review 或 Bad Case 原始 artifacts。

## API

Stage 8EFG 提供以下 endpoints；Full Stage 3EF 后这些接口对 DB run 使用
DB-first 行为，并保留 artifact fallback：

- `GET /api/evaluation/datasets`
- `POST /api/evaluation/datasets`
- `GET /api/evaluation/runs`
- `POST /api/evaluation/run`
- `GET /api/evaluation/results`
- `GET /api/evaluation/summary/{run_id}`
- `GET /api/evaluation/failed-cases`

Bad Case / Evaluation 联动 endpoint：

- `POST /api/bad-cases/from-failed-case`

`POST /api/evaluation/run` 支持 `event`、`flow_counting`、`trajectory`、
`detection`、`tracking`、`regression` 类型。其中 `regression` 读取当前
run 的 `bad_cases.jsonl`，输出 artifact-backed regression summary MVP；
它不执行真实模型重跑。

## Metrics MVP

当前指标是 artifact-backed MVP：

- Event：按 `event_type` 和 frame range overlap / tolerance 做贪心匹配，
  输出 precision、recall、F1，并把 unmatched expected / actual 写为
  failed cases。
- Flow counting：比较 expected counts 与 `flow_counts.json` 的 total、
  class、direction 误差，输出 absolute error、MAE、MAPE。
- Trajectory：从 `trajectory_points.jsonl` 统计 track count、trajectory
  point count、average track length、average speed、direction availability。
- Detection：若没有检测标注，返回 `not_applicable`；不宣称 mAP 已实现。
- Tracking：若没有跟踪标注，返回 `not_applicable`；不宣称 IDF1 / MOTA 已实现。
- Regression：读取 Bad Case status，输出 `total_cases`、`open_cases`、
  `fixed_cases`、`verified_cases`、`ignored_cases`、`fixed_case_count`、
  `reopened_case_count` 和 `regression_pass_rate`。

Bad Case regression MVP 口径：

```text
regression_pass_rate = verified_cases / max(fixed_cases + verified_cases + open_cases, 1)
```

当前没有 reopen 机制，因此 `reopened_case_count` 返回 0。该指标不是
rerun-based regression，也不代表真实模型回归通过率。

## CLI

```bash
python3 scripts/run_evals.py \
  --run-id run_xxx \
  --dataset-id dataset_xxx \
  --evaluation-type event \
  --json
```

可选参数：

- `--results-root`
- `--eval-root`
- `--evaluation-type event|flow_counting|trajectory|detection|tracking|regression`
- `--write-db`
- `--no-write-db`
- `--database-url sqlite:///...`

## 与 Bad Case / Review 的边界

Evaluation failed cases 是评测失败记录，不等于 Bad Case Center 的
`bad_cases.jsonl` 或 `bad_cases` DB rows。Stage 8HI 提供显式转换 MVP；Full
Stage 3EF 后，调用 `POST /api/bad-cases/from-failed-case` 会优先查 DB
`evaluation_results.summary["failed_cases"]`，创建 `source=evaluation_center`、
`linked_failed_case_id=<failed_case_id>` 的 DB Bad Case；DB 缺失时 fallback 到
`evals/results/failed_cases.jsonl` 和 artifact-backed Bad Case 行为。该操作不会
修改 failed case 原始记录。

Review Center 的 `false_positive` / `false_negative` 是人工复核状态，也不是
Evaluation ground truth。Evaluation 可以读取 Stage 6/7 artifacts，但不修改
Review artifacts。
