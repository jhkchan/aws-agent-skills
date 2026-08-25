# Advanced Patterns — SageMaker Pipeline Deployer

Expert-knowledge deep dives and recent-feature notes moved out of the SKILL.md body. Loaded on demand.


## Step 14 — Recent features (2023-2026)

**Recent AWS features (2023-2026):**

- **Pipeline definition config (2023-2024):** `pipeline_definition_config`
  lets you manage the JSON definition as an artifact for CI/CD diffs.
- **FailStep (2023-2024):** dedicated step type for explicit failure
  with custom error message. Replaces raising in a processing script.
- **EMRStep in Pipelines (2023-2024):** launches a transient EMR cluster
  as a step — for Spark workloads beyond the SageMaker Spark container.
- **Richer ModelMetrics (2023-2024):** data quality, model quality,
  bias, explainability metrics surface in Studio and inform approval.
- **Cache-key digest improvements (2024-2025):** SageMaker clarified
  cache-key includes S3 object ETags (not just URIs), closing the
  source-tarball-at-stable-path loophole.
- **InfrastructureConfig (2024-2025):** declarative VPC config on
  Pipeline (instead of per-estimator `subnets` / `security_group_ids`).
