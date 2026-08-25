---
name: sagemaker-model-registry-operator
description: Operates SageMaker Model Registry lifecycles safely — creates model package groups; registers versioned model packages (model artifacts, inference images, metrics, approval status); drives the manual approval workflow (PendingManualApproval to Approved or Rejected); manages model package versions within a group; and distinguishes group-registered from standalone packages. Covers SageMaker Model Cards (auto-populated from packages), the Model Dashboard, and Model Registry with SageMaker Projects for CI/CD model deployment. Runs deterministic pre-checks (artifact accessibility, image availability, metrics S3 reachability, IAM, approval-state legality), emits the exact create-model-package / update-model-package CLI behind a CONFIRM gate, and verifies registry state. Emits READY | BLOCKED | COMPLETED. Use when registering a model, approving for production, listing versions, adopting Model Cards, or wiring Model Registry with SageMaker Projects.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws sagemaker create-model-package-group, create-model-package, update-model-package, describe-model-package, list-model-packages, delete-model-package, create-model-card, describe-model-card, list-mlflow-models, and aws sagemaker list-projects (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AI/ML
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Registering a trained model in SageMaker Model Registry (create-model-package-group, create-model-package), driving the model approval workflow (PendingManualApproval to Approved or Rejected), managing model package versions within a group, distinguishing group-registered packages from standalone packages, listing or describing packages, adopting SageMaker Model Cards (auto-populated from a registered package), using the SageMaker Model Dashboard for a cross-registry view, wiring Model Registry with SageMaker Projects for CI/CD model deployment pipelines, or diagnosing a model package stuck in PendingManualApproval or a Failed registration.
  when_not_to_use: SageMaker endpoint deployment or real-time inference (use sagemaker-endpoint-deployer), SageMaker training job operations (use sagemaker-training-job-operator), SageMaker Studio or domain setup, or non-SageMaker model registries (MLflow open-source on EC2/EKS, HuggingFace Hub).
  activation_triggers: SageMaker Model Registry, model package group, create-model-package, update-model-package, model approval, PendingManualApproval, approve model, reject model, ModelApprovalStatus, Model Card, create-model-card, Model Dashboard, SageMaker Projects, model CI/CD, model versioning, InferenceSpecification, model package ARN, describe-model-package
  invocation_schema: 'Input: either (a) a model registry operation intent (create-group, register-package, approve, reject, list, describe, model-card, projects-integration) with target model package group / package / approval status, OR (b) a model-package-arn + operation for live-account execution. Output: a deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: SageMaker, Model Registry, model package group, model package, model approval, PendingManualApproval, Approved, Rejected, model versioning, Model Card, Model Dashboard, SageMaker Projects, CI/CD model deployment, inference specification, model metrics, model artifacts, InferenceSpecification, model package ARN
  tags: sagemaker, ai-ml, model-registry, mlops, operate, model-approval, model-cards
---

# SageMaker Model Registry Operator

## What this skill does

Executes SageMaker Model Registry operations correctly and
safely. Runs deterministic pre-checks before any state-changing
CLI, emits the exact `create-model-package` / `update-model-package`
sequence behind a CONFIRM gate, and verifies registry state
transitions after apply. Every registration surfaces approval
status, inference specification, and metrics wiring.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority + approval-state legality | Before any operation |
| **§ Mindset** | Approval-gated deployability, versioning, group vs standalone | Understanding the safety model |
| **§ Pre-flight** | Artifact / image / metrics / IAM metadata gate | Before executing any CLI |
| **§ Process** | Per-operation planning: create-group, register, approve, reject, model-card, projects | When choosing which operation |
| **§ Common patterns** | Group-registered, standalone, Model Card, Projects CI/CD boilerplate | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, COMMANDS, POST_VERIFY | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes | Review before risky operations |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (artifact S3 unreachable, inference image inaccessible, metrics S3 missing, IAM permission missing, approval-state transition illegal, group does not exist for group-registered package) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Operation applied and post-verification passed (package registered with correct `ModelApprovalStatus`, package version incremented, Model Card created, approval transition reflected) | Emit `describe-model-package` summary |

**Priority order for pre-checks (all must pass for READY):**

1. **Model artifact accessibility** — `model.tar.gz` S3 object exists and the caller's execution role has `s3:GetObject` on the artifact prefix.
2. **Inference image availability** — every container image in `InferenceSpecification.Containers[].Image` exists in ECR and the caller has `ecr:BatchGetImage`.
3. **Metrics S3 reachability** — every `ModelMetrics` S3 URI resolves and the caller has read access.
4. **Model package group existence** (for group-registered packages) — `ModelPackageGroupName` resolves to an existing group.
5. **IAM permissions** — caller holds `sagemaker:CreateModelPackage`, `UpdateModelPackage`, `DescribeModelPackage`, `CreateModelPackageGroup`.
6. **KMS key (if registry is encrypted)** — caller has `kms:Decrypt` and `kms:GenerateDataKey` on the registry's KMS key.
7. **Approval-state transition legality** — `PendingManualApproval → Approved` or `Rejected` is legal; `Approved → PendingManualApproval` requires explicit re-registration.

**Approval state machine (2026):**

| Current state | Allowed transitions | Notes |
|---|---|---|
| `PendingManualApproval` | `Approved`, `Rejected` | Default for new packages when approval is manual |
| `Approved` | `Rejected` (rollback) | Re-approval to PendingManualApproval requires a new package version |
| `Rejected` | `Approved` (rare) | Generally re-register a new version |
| `AutoApproved` (auto-approval mode) | `Rejected` | Set via `ModelApprovalStatus` on the group |

## Mindset

Three Model Registry realities drive every operation:

- **`PendingManualApproval` is the safety gate, not a default.**
  A model package registered with `ModelApprovalStatus:
  PendingManualApproval` cannot be deployed by downstream CI/CD
  (SageMaker Projects, EventBridge rules) until a human
  explicitly transitions it to `Approved`. Setting `Approved`
  at registration time bypasses review — only do this for
  dev / sandbox registries.

- **Model package groups are the versioning boundary.** A
  group-registered package (`ModelPackageGroupName` set) gets
  an auto-incremented `ModelPackageVersion` within the group.
  A standalone package (no group) is a one-off with no version
  lineage. Group-registered is the production pattern;
  standalone is for experimentation only.

- **`InferenceSpecification` is what makes a package deployable.**
  A package with `InferenceSpecification` (containers, supported
  instance types, content types) can be deployed to a SageMaker
  endpoint. A package registered as a model card source only
  (no inference spec) is non-deployable — useful for
  documentation but not for serving.

## Pre-flight: model package metadata gate

Run before classification. `list-model-packages` returns max
100/page (`--max-results 100`, paginate with `--next-token`).

**Live-account pre-flight (skip if offline plan):**
Live-account pre-flight commands 1-7 (describe-model-package-group, list-model-packages, s3api head-object on the artifact and every metrics URI, ecr describe-images, iam simulate-principal-policy, kms describe-key): [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before executing any live-account CLI.

**Malformed input:** emit `VERDICT: ERROR` with reason and remediation.

| Attribute | Effect on operation |
|---|---|
| `ModelPackageGroupStatus: Pending` | Group creation in progress; wait for `Completed` before registering |
| `ModelPackageGroupName` missing | Standalone package — no versioning; warn operator |
| `ModelApprovalStatus: Approved` at registration | Bypasses review; flag as risky for production |
| `InferenceSpecification` missing | Non-deployable package (documentation only) |
| `ModelMetrics` S3 URI returns 404 | Registration accepted but metrics unavailable; downstream Model Card incomplete |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Model Registry behaviors
The 13 non-obvious behaviors (group-registered vs standalone, approval set at registration, update-model-package as the only transition path, package immutability, Model Card auto-populate, Projects CI/CD wiring, AdditionalInferenceSpecifications, Marketplace SourceAlgorithms, ARN as canonical ID, ValidationSpecification, KMS scope, rejected-not-deleted): [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a pre-check fails or a transition looks illegal.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks. If ANY fails, verdict is BLOCKED with
failures in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Caller holds `sagemaker:CreateModelPackage` /
   `UpdateModelPackage` / `DescribeModelPackage` /
   `CreateModelPackageGroup`.
2. KMS key (if configured) decryptable by the caller.

**For create-group:**
3. `ModelPackageGroupName` unique in account-region (3-63 chars,
   `[a-zA-Z0-9](-[a-zA-Z0-9])*`).
4. `KmsKeyId` (if specified) is enabled and the caller can use it.

**For register-package (group-registered):**
3. `ModelPackageGroupName` resolves to an existing group with
   `ModelPackageGroupStatus: Completed`.
4. Model artifact S3 object (`model.tar.gz`) exists and the
   caller's role has `s3:GetObject`.
5. Every inference image in `InferenceSpecification.Containers`
   exists in ECR; caller has `ecr:BatchGetImage`.
6. Every `ModelMetrics` S3 URI resolves.
7. `ModelApprovalStatus` is one of `PendingManualApproval`,
   `Approved`, `Rejected`.

**For register-package (standalone):**
3. `ModelPackageName` unique in account-region.
4. Same artifact / image / metrics checks as above.
5. Warn that standalone packages have no versioning lineage.

**For approve / reject (update-model-package):**
3. `ModelPackageArn` resolves to an existing package.
4. Current `ModelApprovalStatus` allows the requested transition
   (see approval state machine above).
5. For `Approved` transitioning to deployment, the package has
   an `InferenceSpecification` (otherwise non-deployable).

**For model-card:**
3. Source model package (if `--source-uri-type ModelPackage`)
   exists and is registered.
4. `ModelCardName` unique in account-region.

**For projects-integration:**
3. SageMaker Project exists
   (`sagemaker describe-project --project-name <name>`).
4. The project's service role has `sagemaker:CreateModel` and
   `sagemaker:CreateEndpointConfig` for the deploy stage.
5. The project's designated model package group has at least one
   `Approved` package version (or the pipeline will stall).

### Step 2: READY — emit operation plan

Emit `VERDICT: READY` with exact CLI sequence + CONFIRM gate:
- Exact AWS CLI command with all flags populated.
- Expected next version number (for group-registered packages).
- Expected downstream effects (SageMaker Projects pipeline
  trigger on `Approved`, Model Card auto-population).
- CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  CLI (`create-model-package-group`, `create-model-package`,
  `update-model-package`, `delete-model-package`,
  `create-model-card`), emit CONFIRM prompt. Do NOT execute
  until confirmed.
- Snapshot current state:
  `describe-model-package-group --model-package-group-name <group> --output json > /tmp/<group>-backup-$(date +%s).json`.
- Execute the CLI.
- For group-registered packages, capture the returned
  `ModelPackageArn` and `ModelPackageVersion`.

### Step 4: Post-verification — COMPLETED

ALL checks must pass for `COMPLETED`:
1. `describe-model-package --model-package-arn <arn>` returns
   the expected `ModelApprovalStatus`, `ModelPackageVersion`,
   `InferenceSpecification`.
2. Group-registered: `list-model-packages --model-package-group-name <group>`
   shows the new version.
3. Approval transitions: the new status is reflected in
   `describe-model-package`.
4. For Model Card operations: `describe-model-card --model-card-name <name>`
   returns `ModelCardStatus: Draft` or `PendingReview`, and
   `Content` reflects the source package.
5. For Projects integration: the CodePipeline execution is
   triggered (or queued) on the `Approved` transition; check
   via `codepipeline list-pipeline-executions --pipeline-name <name>`.
6. For packages with `ValidationSpecification`: all validation
   jobs reached `Completed`; otherwise the package is not
   registered.

If ANY verification fails, emit `VERDICT: ERROR` — do not claim COMPLETED.

## Common registry patterns (boilerplate)

### Create a model package group (one-time per model lineage)

```bash
aws sagemaker create-model-package-group \
  --model-package-group-name "fraud-detection-classifier" \
  --model-package-group-description "Production fraud detection model lineage (XGBoost lineage)" \
  --tags '[{"Key":"team","Value":"risk-platform"},{"Key":"cost-center","Value":"ml-1234"}]'
```

The group ARN is `arn:aws:sagemaker:<region>:<account>:model-package-group/<name>`.
All versioned packages registered against this group share the
lineage.

### Register a versioned model package (group-registered)

```bash
aws sagemaker create-model-package \
  --model-package-name "fraud-detection-2026-08-v1" \
  --model-package-group-name "fraud-detection-classifier" \
  --inference-specification '{
    "Containers": [
      {
        "Image": "763104351884.dkr.ecr.us-east-1.amazonaws.com/xgboost-inference:1.7-1-cpu-py3",
        "ImageDigest": "sha256:abc123...",
        "ModelDataUrl": "s3://ml-models/fraud-detection/2026-08/output/model.tar.gz",
        "Framework": "XGBOOST",
        "FrameworkVersion": "1.7-1",
        "NearestModelName": "XGBoost"
      }
    ],
    "SupportedTransformInstanceTypes": ["ml.m5.4xlarge"],
    "SupportedRealtimeInferenceInstanceTypes": ["ml.m5.large", "ml.m5.xlarge", "ml.m5.2xlarge"],
    "SupportedContentTypes": ["text/csv", "application/json"],
    "SupportedResponseMIMETypes": ["text/csv", "application/json"]
  }' \
  --model-metrics '{
    "ModelQuality": {"Statistics": {"ContentType": "application/json", "S3Uri": "s3://ml-metrics/fraud-detection/2026-08/quality.json"}},
    "ModelDataQuality": {"Statistics": {"ContentType": "application/json", "S3Uri": "s3://ml-metrics/fraud-detection/2026-08/data-quality.json"}},
    "Bias": {"Report": {"ContentType": "application/json", "S3Uri": "s3://ml-metrics/fraud-detection/2026-08/bias.json"}},
    "Explainability": {"Report": {"ContentType": "application/json", "S3Uri": "s3://ml-metrics/fraud-detection/2026-08/explainability.json"}}
  }' \
  --approval-status PendingManualApproval \
  --tags '[{"Key":"trained-by","Value":"sagemaker-training-job-fraud-2026-08"}]'
```

The next version number is auto-assigned (e.g., version 5 if the
latest existing version is 4). Capture the returned
`ModelPackageArn` for downstream operations.

### Approve a model package for production

```bash
aws sagemaker update-model-package \
  --model-package-arn arn:aws:sagemaker:us-east-1:111122223333:model-package/fraud-detection-classifier/5 \
  --model-approval-status Approved \
  --approval-description "Approved by risk-platform review board 2026-08-11. AUC=0.94, no bias drift vs 2026-07 model."
```

If a SageMaker Projects deployment pipeline is wired to this
group, the `Approved` transition triggers an EventBridge event
that the pipeline consumes — the deploy stage runs automatically.

### Reject a model package

```bash
aws sagemaker update-model-package \
  --model-package-arn arn:aws:sagemaker:us-east-1:111122223333:model-package/fraud-detection-classifier/5 \
  --model-approval-status Rejected \
  --approval-description "Rejected: precision@threshold=0.62 below 0.75 target."
```

A rejected package remains in the registry for audit but cannot
be deployed by the Projects pipeline.

### Standalone model package (no group, no versioning)

```bash
aws sagemaker create-model-package \
  --model-package-name "experimental-bert-2026-08-11" \
  --inference-specification '{
    "Containers": [
      {"Image": "763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-inference:2.3.0-transformers4.39-cpu-py311-ubuntu22.04",
       "ModelDataUrl": "s3://ml-models/experimental/bert-2026-08-11/model.tar.gz"}
    ],
    "SupportedRealtimeInferenceInstanceTypes": ["ml.g5.xlarge"]
  }' \
  --approval-status PendingManualApproval
```

No `ModelPackageGroupName` means standalone — no version
increment, no group-level lineage. Use for experimentation;
do not use for production tracking.

### Auto-populate a SageMaker Model Card from a package

```bash
aws sagemaker create-model-card \
  --model-card-name "fraud-detection-2026-08-card" \
  --model-card-status "PendingReview" \
  --model-card-content '{"version":"1.0","model_overview":{"model_creator":"risk-platform","model_artifact":"s3://ml-models/fraud-detection/2026-08/output/model.tar.gz"},"intended_uses":{"purpose_of_model":"Real-time fraud scoring","intended_uses":"Payment fraud detection"}}' \
  --source-uri arn:aws:sagemaker:us-east-1:111122223333:model-package/fraud-detection-classifier/5 \
  --source-uri-type ModelPackage
```

The card inherits the package's `InferenceSpecification`, metrics
URIs, and approval status. Edit `model_card_content` for the
subjective sections (intended uses, risks, recommendations).

### SageMaker Projects CI/CD pipeline (auto-deploy on approval)

A SageMaker Project created from the `MLOps template for model
deployment` provisions a CodePipeline that consumes `Approved`
events from the project's model package group, a CodeBuild
project that runs the deploy script (`deploy.py` or `build.py`)
to create the SageMaker model / endpoint config / endpoint, and
an EventBridge rule that fires on
`SageMaker Model Package Approval` for the group.

Verify the wiring:

```bash
aws sagemaker describe-project --project-name "fraud-detection-deploy-proj"
aws codepipeline list-pipelines --query 'pipelines[?contains(name, `fraud-detection`)]'
aws events list-rule-names-by-target --target-arn arn:aws:codepipeline:us-east-1:111122223333:fraud-detection-deploy
```

When a new package version transitions to `Approved`, the pipeline
triggers within seconds.

## Diagnostic flows

The three diagnostic flows (package stuck in PendingManualApproval, Projects pipeline did not trigger on approval, Model Card content mismatch): [references/error-handling.md](references/error-handling.md).
Load on demand when diagnosing a stalled approval or a silent CI/CD trigger.

## Output format (per operation)

```text
OPERATION: <create-group | register-package | approve | reject | list | describe | model-card | projects-integration>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <group-name / package-arn / version, region>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <verify command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <PendingManualApproval | Approved | Rejected | registered> after apply>
VERSION: <next or current ModelPackageVersion, or N/A>
NOTES: <approval rationale, versioning, downstream pipeline effects>
```

### Worked example — register group-registered package (READY)

```text
OPERATION: register-package
VERDICT: READY
TARGET: fraud-detection-classifier / next version 5, us-east-1
PRE_CHECKS:
  - [PASS] describe-model-package-group fraud-detection-classifier exists, Status Completed
  - [PASS] list-model-packages latest version 4; next version 5
  - [PASS] s3api head-object s3://ml-models/fraud-detection/2026-08/output/model.tar.gz returns 200
  - [PASS] ecr describe-images xgboost-inference:1.7-1-cpu-py3 imageTag exists
  - [PASS] s3api head-object on all four ModelMetrics URIs returns 200
  - [PASS] Caller holds sagemaker:CreateModelPackage, iam:PassRole
  - [PASS] KMS key arn:aws:kms:us-east-1:111122223333:key/abc decryptable
  - [PASS] Approval status PendingManualApproval — safe default for production lineage
STEPS:
  1. CONFIRM: About to create-model-package fraud-detection-2026-08-v1 in group fraud-detection-classifier (version 5) in account 111122223333 region us-east-1. Approval status PendingManualApproval (requires manual approval before deployment). Proceed? (yes/no)
  2. aws sagemaker create-model-package --model-package-name fraud-detection-2026-08-v1 --model-package-group-name fraud-detection-classifier --inference-specification '{"Containers":[{"Image":"763104351884.dkr.ecr.us-east-1.amazonaws.com/xgboost-inference:1.7-1-cpu-py3","ModelDataUrl":"s3://ml-models/fraud-detection/2026-08/output/model.tar.gz","Framework":"XGBOOST","FrameworkVersion":"1.7-1"}],"SupportedRealtimeInferenceInstanceTypes":["ml.m5.large","ml.m5.xlarge","ml.m5.2xlarge"],"SupportedContentTypes":["text/csv"],"SupportedResponseMIMETypes":["text/csv"]}' --model-metrics '{"ModelQuality":{"Statistics":{"ContentType":"application/json","S3Uri":"s3://ml-metrics/fraud-detection/2026-08/quality.json"}}}' --approval-status PendingManualApproval
  3. aws sagemaker describe-model-package --model-package-arn <returned-arn>
POST_VERIFY:
  - (pending execution) describe-model-package returns ModelPackageVersion 5, ModelApprovalStatus PendingManualApproval
  - (pending execution) list-model-packages --model-package-group-name fraud-detection-classifier shows version 5
STATE: pending — will be PendingManualApproval
VERSION: 5
NOTES:
  - Versioning: group-registered; version auto-incremented to 5. Standalone packages do not increment versions.
  - Approval: PendingManualApproval requires explicit update-model-package to Approved before deployment.
  - Downstream: if SageMaker Projects is wired, the pipeline triggers only on the Approved transition (not on registration).
```

### Worked example — approve blocked (BLOCKED)
Full BLOCKED worked example (approve blocked — no InferenceSpecification): [references/worked-examples.md](references/worked-examples.md).
The READY example above is the primary worked example; this one loads on demand.

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
OPERATION: <create-group | register-package | approve | reject | list | describe | model-card | projects-integration>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <group-name / package-arn / version, region>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> on <group / package> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command with every flag populated — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <PendingManualApproval | Approved | Rejected | registered | pending>
VERSION: <ModelPackageVersion or N/A>
NOTES: <approval rationale — must state PendingManualApproval | Approved | Rejected and why; versioning; downstream pipeline effects>
```

### FORBIDDEN output patterns

- NEVER start with conversational preamble ("Let me analyze…") — the VERDICT block is the FIRST line, always. Use uppercase verdict values only (`READY`, `BLOCKED`, `COMPLETED`).
- NEVER omit PRE_CHECKS — every pre-check must appear with `[PASS]` or `[FAIL]` and a specific reason for each failure.
- NEVER register a production model package with `--approval-status Approved` without flagging the bypass-review risk in NOTES.
- NEVER list a CLI command with placeholder flags in a READY plan — every flag must be populated with actual values from the input data.
- NEVER claim COMPLETED without every POST_VERIFY line showing `[PASS]`, and never omit the CONFIRM gate as the first STEPS entry for state-changing operations.

## Anti-Patterns — NEVER do these things

- NEVER register a production model package without a `ModelPackageGroupName`. Standalone packages have no versioning lineage and cannot be tracked through the approval workflow consistently. Use group-registered packages for production.
- NEVER set `--approval-status Approved` at registration time for a production lineage. The default `PendingManualApproval` exists to gate deployment behind human review; auto-approval bypasses this safety check.
- NEVER assume a registered package is deployable without an `InferenceSpecification`. Packages registered for Model Card sourcing only (documentation) cannot be deployed to an endpoint. Verify the spec before approving.
- NEVER assume `update-model-package` rollbacks (`Approved → Rejected`) propagate automatically to deployed endpoints. The endpoint continues serving the previously-deployed version until the SageMaker Projects pipeline (or manual update) re-deploys.
- NEVER use `delete-model-package` to "revert" a version. Deletion removes the package from the registry for audit purposes and the version number is not reused. To revert, register a new version pointing at the prior artifact.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE** before any state-changing CLI.
- **Snapshot before modification:** `describe-model-package-group --model-package-group-name <group> --output json > /tmp/<group>-backup-$(date +%s).json`.
- **Verify model artifact S3 accessibility** before registration — a 404 at registration time leaves an empty package version.
- **Verify all inference images exist in ECR** before registration.
- **Prefer group-registered packages** over standalone for any production lineage.

## Expert heuristic: "Approval is a deployment gate, not a label"
The full heuristic — registration lifecycle diagram, approval-state transition matrix, group vs standalone decision table, per-operation pre-check table: [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when planning approvals or CI/CD wiring.

## Recent AWS features (2024-2026)
Recent AWS features 2024-2026 (Model Cards, Model Dashboard, Registry+Projects auto-deploy, Additional Inference Specifications, registry KMS, ValidationSpecification, Customer Metadata Properties, MLflow lineage, EventBridge state change, cross-account dashboard): [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a feature question arises.

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — Step 0 expert-knowledge deep dive, the approval-as-deployment-gate heuristic (lifecycle diagram, transition matrix, per-operation pre-checks), recent AWS features (2024-2026)
- [Diagnostic commands](references/diagnostic-commands.md) — live-account pre-flight command listing (group, versions, artifact, ECR image, metrics, IAM, KMS)
- [Error handling](references/error-handling.md) — diagnostic flows: package stuck in PendingManualApproval, Projects pipeline not triggering, Model Card content mismatch
- [Worked examples](references/worked-examples.md) — secondary worked example (approve blocked without InferenceSpecification)
- [Approval workflow and CI/CD pipeline](references/approval-workflow-and-cicd-pipeline.md) — approval workflow and SageMaker Projects CI/CD detail
- [Model cards, dashboard, and packages](references/model-cards-dashboard-and-packages.md) — Model Cards, Model Dashboard, and model package detail

## Domain

AWS CloudOps / AI-ML — Model Registry & MLOps Operations.

## AWS documentation

- **SageMaker Model Registry** — https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry.html
- **Model Package Groups** — https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry-groups.html
- **Register a Model Package** — https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry-register-version.html
- **Approve Model Packages** — https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry-approve.html
- **SageMaker Model Cards** — https://docs.aws.amazon.com/sagemaker/latest/dg/model-cards.html
- **SageMaker Model Dashboard** — https://docs.aws.amazon.com/sagemaker/latest/dg/model-dashboard.html
- **SageMaker Projects / MLOps templates** — https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-projects.html
- **AWS CLI / API Reference** — https://docs.aws.amazon.com/cli/latest/reference/sagemaker/
