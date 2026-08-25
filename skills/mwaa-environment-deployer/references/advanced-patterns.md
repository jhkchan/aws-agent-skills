# Advanced Patterns — MWAA Environment Deployer

## Expert heuristic: execution class sizing by concurrent DAG count

A baseline model says "use mw1.medium." The correct heuristic sizes
based on concurrent DAG and task count.

```text
Execution class sizing:
  ├── mw1.small (~$0.55/hour)
  │     Suitable for: < 25 concurrent DAG runs, < 5 tasks per DAG
  │     Max workers: 1-25
  │     Use case: dev/test, small team, low DAG count
  │     Cost: ~$400/month
  │
  ├── mw1.medium (~$1.10/hour)
  │     Suitable for: 25-75 concurrent DAG runs, moderate task density
  │     Max workers: 1-50
  │     Use case: production, medium team, moderate DAG count
  │     Cost: ~$800/month
  │
  ├── mw1.large (~$2.20/hour)
  │     Suitable for: 75-200+ concurrent DAG runs, high task density
  │     Max workers: 1-100
  │     Use case: large-scale production, enterprise, mission-critical pipelines
  │     Cost: ~$1600/month
  │
  └── Sizing rule: count peak concurrent DAG runs × avg tasks per DAG
        < 100 concurrent tasks → mw1.small
        100-500 concurrent tasks → mw1.medium
        500+ concurrent tasks → mw1.large
```

**Key implication:** the execution class determines both cost AND the
maximum number of workers. Under-sizing causes task queuing (DAGs run
slowly). Over-sizing wastes money. Count peak concurrent tasks, not
total DAGs — a DAG that runs once a day contributes 1 task at peak, not
its total lifetime task count.

## Recent AWS features (2023-2026)

**Recent AWS features (2023-2026):**

- **MWAA Airflow 2.9+ support (2024-2025):** MWAA now supports Airflow
  2.9 and 2.10, including the new TaskFlow API improvements, dynamic
  task mapping enhancements, and dataset-aware scheduling.

- **Python 3.11 support (2024-2025):** MWAA environments on Airflow
  2.9+ use Python 3.11. Older environments on Airflow 2.7 use Python
  3.10. Verify package compatibility when upgrading.

- **Startup script support (2024-2025):** The `--startup-script-s3-path`
  parameter allows running a bash script at worker startup, useful for
  installing system-level dependencies or running initialization code.

- **Environment class auto-scaling improvements (2024-2025):** MWAA
  improved auto-scaling heuristics for mw1.medium and mw1.large,
  reducing task queue times for bursty workloads.

- **Terraform provider maturity (2024-2025):** The Terraform
  `aws_mwaa_environment` resource now supports startup/shutdown time,
  KMS encryption, all 4 log types, and Airflow configuration overrides.

- **PRIVATE_ONLY webserver mode (2023-2024):** PRIVATE_ONLY mode is now
  GA, enabling compliance-sensitive deployments with no public webserver
  endpoint.

- **MWAA local runner (2024-2025):** The open-source MWAA local runner
  Docker image allows testing DAGs and requirements.txt locally before
  deploying to MWAA.

