# Model Cards, Dashboard, and packages — deep reference

This reference expands the SKILL.md sections on SageMaker Model
Cards, the Model Dashboard, model package group vs standalone
distinctions, Additional Inference Specifications, and Model
Metrics. Load when creating a Model Card, navigating the
Dashboard, or deciding between group-registered and standalone
packages.

## Group-registered vs standalone packages

### Decision matrix

| Factor | Group-registered | Standalone |
|---|---|---|
| Versioning | Auto-incremented `ModelPackageVersion` | No versioning; unique name only |
| Approval workflow | Consistent across versions; pipeline filters by group | Per-package; no lineage continuity |
| Listing | `list-model-packages --model-package-group-name <group>` | `list-model-packages` without filter |
| Model Card source | Card tracks the group lineage | Card tracks one package |
| SageMaker Projects | Project binds to a group | Not supported (Projects require a group) |
| Deletion | Group survives package deletion; version numbers not reused | Package deletion removes it entirely |
| Recommendation | Always for production | Experimentation only |

### How version numbers are assigned

For group-registered packages, SageMaker auto-assigns the next
version number within the group:

- Group "fraud-detection-classifier" has versions 1, 2, 3, 4.
- Next `create-model-package` with this group gets version 5.
- If version 3 is `delete-model-package`'d, the next registration
  still gets version 6 — version 3 is not reused.

For standalone packages, there is no version number; the
`ModelPackageName` is the unique identifier.

### Cross-group promotion

To promote a package across groups (dev → staging → prod):

```bash
# Read the source package's InferenceSpecification and ModelMetrics:
aws sagemaker describe-model-package \
  --model-package-arn arn:aws:sagemaker:us-east-1:111122223333:model-package/fraud-detection-staging/8 \
  --query '{inference:InferenceSpecification,metrics:ModelMetrics,artifact:SourceAlgorithmSpecification}' \
  > /tmp/source-pkg.json

# Register in the target group with the same spec:
aws sagemaker create-model-package \
  --model-package-name "fraud-detection-prod-2026-08-12" \
  --model-package-group-name "fraud-detection-prod" \
  --inference-specification file:///tmp/inference.json \
  --model-metrics file:///tmp/metrics.json \
  --approval-status PendingManualApproval \
  --customer-metadata-properties '{"promoted-from":"fraud-detection-staging/8","promoted-by":"risk-platform"}'
```

The promotion re-registers the same artifact in the target group;
the version number is independent.

## Additional Inference Specifications

### When to use multiple specs

- A model needs both GPU and CPU serving (different instance
  types, possibly different serving images).
- A model is served via multiple frameworks (TensorFlow Serving,
  Triton, PyTorch).
- A/B testing between serving configurations.

### Definition

```bash
aws sagemaker create-model-package \
  --model-package-name "bert-multivariant-2026-08" \
  --model-package-group-name "bert-classifier" \
  --inference-specification '{
    "Containers": [
      {"Image": "<gpu-image>", "ModelDataUrl": "s3://ml-models/bert/2026-08/model.tar.gz"}
    ],
    "SupportedRealtimeInferenceInstanceTypes": ["ml.g5.xlarge", "ml.g5.2xlarge"]
  }' \
  --additional-inference-specifications '[
    {
      "Name": "cpu-variant",
      "Description": "CPU-only variant for low-throughput endpoints",
      "Containers": [
        {"Image": "<cpu-image>", "ModelDataUrl": "s3://ml-models/bert/2026-08/model.tar.gz"}
      ],
      "SupportedRealtimeInferenceInstanceTypes": ["ml.m5.large", "ml.m5.xlarge"]
    }
  ]' \
  --approval-status PendingManualApproval
```

### Deploy-time selection

The deploy script (or the SageMaker Projects deploy stage) selects
the spec via `InferenceSpecificationName` when creating the model:

```bash
aws sagemaker create-model \
  --model-name "bert-prod-cpu" \
  --primary-container '{
    "Image": "<cpu-image>",
    "ModelDataUrl": "s3://ml-models/bert/2026-08/model.tar.gz"
  }' \
  --execution-role-arn arn:aws:iam::111122223333:role/sagemaker-exec
```

Without specifying `InferenceSpecificationName`, the primary
`InferenceSpecification` is used.

## Model Metrics

### Metric types

| Field | What it captures | Source |
|---|---|---|
| `ModelQuality` | Accuracy, AUC, precision, recall, F1 | `Quality.json` from Model Monitor or manual evaluation |
| `ModelDataQuality` | Data drift statistics | Model Monitor baseline constraints |
| `Bias` | Pre-training and post-training bias metrics | SageMaker Clarify |
| `Explainability` | SHAP values, feature importance | SageMaker Clarify |

### JSON structure

Each metrics file is a JSON document with `S3Uri` and
`ContentType`:

```json
{
  "ModelQuality": {
    "Statistics": {
      "ContentType": "application/json",
      "S3Uri": "s3://ml-metrics/fraud-detection/2026-08/quality.json"
    }
  },
  "ModelDataQuality": {
    "Statistics": {
      "ContentType": "application/json",
      "S3Uri": "s3://ml-metrics/fraud-detection/2026-08/data-quality.json"
    }
  },
  "Bias": {
    "Report": {
      "ContentType": "application/json",
      "S3Uri": "s3://ml-metrics/fraud-detection/2026-08/bias.json"
    }
  },
  "Explainability": {
    "Report": {
      "ContentType": "application/json",
      "S3Uri": "s3://ml-metrics/fraud-detection/2026-08/explainability.json"
    }
  }
}
```

### Pre-flight validation

Always run `aws s3api head-object --bucket <bucket> --key <key>`
on each metrics URI before registration. A 404 at registration
time does NOT fail the registration — the package is created
with dangling metrics URIs, and the Model Card shows empty
sections.

## SageMaker Model Cards

### Card lifecycle states

| State | Meaning | Transition |
|---|---|---|
| `Draft` | Authoring in progress; not visible to reviewers | Author submits → `PendingReview` |
| `PendingReview` | Reviewer evaluating; visible in Dashboard | Reviewer approves → `Approved`; rejects → `Draft` |
| `Approved` | Card content reviewed; archived | Archive → `Archived` |
| `Archived` | Read-only; historical record | Terminal |

### Card content schema

```json
{
  "version": "1.0",
  "model_overview": {
    "model_creator": "risk-platform",
    "model_artifact": "s3://ml-models/fraud-detection/2026-08/output/model.tar.gz",
    "inference_environment": {"container_image": ["<image-uri>"]},
    "model_owner": "risk-platform@example.com"
  },
  "intended_uses": {
    "purpose_of_model": "Real-time fraud scoring for checkout transactions",
    "intended_uses": "Online payment fraud detection on the checkout API",
    "out_of_scope_uses": ["Not for batch post-hoc analysis", "Not for non-payment fraud"],
    "risk_rating": "Medium",
    "risks": ["Model may exhibit bias against under-represented geographies"]
  },
  "business_details": {
    "business_problem": "Reduce chargeback rate from fraudulent transactions",
    "business_stakeholders": ["payments@example.com"]
  },
  "evaluation_details": [
    {
      "name": "AUC evaluation 2026-08",
      "evaluation_observation": "AUC=0.94 on hold-out test set",
      "evaluation_job": "sagemaker-processing-eval-2026-08",
      "datasets": ["s3://ml-datasets/fraud-eval/2026-08/"]
    }
  ]
}
```

### Auto-population from a package

When `--source-uri <arn> --source-uri-type ModelPackage` is set:

- `model_overview.model_artifact` is populated from the
  package's `InferenceSpecification.Containers[0].ModelDataUrl`.
- `model_overview.inference_environment.container_image` is
  populated from the package's image URIs.
- `evaluation_details` is populated from the package's
  `ModelMetrics` (quality, bias, explainability).
- `model_overview.model_approval_status` reflects the current
  approval status (snapshot at card creation).

Subsequent package updates do NOT refresh the card. Re-create
the card or use `update-model-card` to refresh.

### Card review workflow

1. Author creates the card in `Draft` state.
2. Author submits for review: `update-model-card-status --model-card-status PendingReview`.
3. Reviewer reads the card in the Model Dashboard, adds comments.
4. Reviewer approves: `update-model-card-status --model-card-status Approved`.
5. Card is archived; further edits require a new card version.

## Model Dashboard

### What the Dashboard shows

The SageMaker Model Dashboard (in SageMaker Studio and the AWS
console) is a unified view across:

- Model Registry packages (group-registered and standalone).
- Model Cards (linked to packages).
- Endpoints (linked to deployed packages).
- Training jobs (linked to the package's source artifact).

### Cross-cutting filters

- Approval status (Pending / Approved / Rejected).
- Model package group.
- Tags.
- Creation date.
- Account / region (with cross-account configuration).

### Programmatic access

The Dashboard surfaces data available via the SageMaker API:

```bash
# List all packages across groups:
aws sagemaker list-model-packages --max-results 100

# List Model Cards:
aws sagemaker list-model-cards --max-results 100

# List endpoints:
aws sagemaker list-endpoints --max-results 100

# Correlate via CustomerMetadataProperties or tags.
```

For an integrated lineage view including MLflow runs:

```bash
aws sagemaker list-mlflow-models --max-results 100
```

### Cross-account / cross-region (2025-2026)

The Dashboard aggregates packages across accounts and regions
when SageMaker Studio is configured with cross-account
permissions. The operator sees packages from dev, staging, and
prod accounts in one view, with the account / region displayed
per row.

## Common pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Registering without `--model-package-group-name` | No versioning; package does not appear in Projects pipeline | Re-register with the group; the standalone package remains for audit |
| Setting `--approval-status Approved` at registration | Bypasses review; package auto-deployed | Set `PendingManualApproval`; review then `update-model-package` |
| Missing `InferenceSpecification` | Package registered but non-deployable | Re-register with the spec; or register a new version |
| Model Card content empty after `--source-uri` | Source package had no metrics | Upload metrics to the package's `ModelMetrics` S3 URIs and re-create the card |
| Additional Inference Specifications not selectable at deploy | Deploy script does not pass `InferenceSpecificationName` | Update the deploy script to accept and pass the spec name |
| KMS-encrypted registry, deployer lacks `kms:Decrypt` | Endpoint creation fails with `KMSAccessDenied` | Add `kms:Decrypt` on the registry KMS key to the deployer role |
