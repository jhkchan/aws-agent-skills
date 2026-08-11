# End-to-end usage scenario: sagemaker-model-registry-operator

A walkthrough showing the skill planning the registration of a
versioned XGBoost model package (version 5 of the
`fraud-detection-classifier` group) with `PendingManualApproval`,
full `InferenceSpecification`, and `ModelMetrics` wired. This
exercises Step 0 (target capture), Step 1 (pre-flight: artifact,
image, metrics, IAM, KMS), Step 2 (register-package), and Step 4
(post-verify with version increment).

## Input (user prompt)

> Register "fraud-detection-2026-08-v1" in `us-east-1` as version
> 5 of group "fraud-detection-classifier" (group exists,
> Completed, latest version 4). Artifact
> `s3://ml-models/fraud-detection/2026-08/output/model.tar.gz`.
> Image
> `763104351884.dkr.ecr.us-east-1.amazonaws.com/xgboost-inference:1.7-1-cpu-py3`.
> Metrics at `s3://ml-metrics/fraud-detection/2026-08/` (quality,
> bias, explainability, data-quality). Approval status
> PendingManualApproval. KMS key
> `arn:aws:kms:us-east-1:111122223333:key/abc`. Caller holds
> `sagemaker:CreateModelPackage`.

## Skill output

```text
OPERATION: register-package
VERDICT: READY
TARGET: fraud-detection-classifier / next version 5, us-east-1
PRE_CHECKS:
  - [PASS] describe-model-package-group fraud-detection-classifier
    exists, Status Completed
  - [PASS] list-model-packages latest version 4; next version 5
  - [PASS] s3api head-object
    s3://ml-models/fraud-detection/2026-08/output/model.tar.gz
    returns 200 (caller role has s3:GetObject)
  - [PASS] ecr describe-images
    xgboost-inference:1.7-1-cpu-py3 imageTag exists
  - [PASS] s3api head-object on all four ModelMetrics URIs
    returns 200 (quality, bias, explainability, data-quality)
  - [PASS] Caller holds sagemaker:CreateModelPackage
  - [PASS] KMS key arn:aws:kms:us-east-1:111122223333:key/abc
    decryptable
  - [PASS] Approval status PendingManualApproval — safe default
    for production lineage (requires manual approval before
    deployment)
STEPS:
  1. CONFIRM: About to create-model-package
     fraud-detection-2026-08-v1 in group
     fraud-detection-classifier (version 5) in account
     111122223333 region us-east-1. Approval status
     PendingManualApproval. Proceed? (yes/no)
  2. aws sagemaker create-model-package \
       --model-package-name fraud-detection-2026-08-v1 \
       --model-package-group-name fraud-detection-classifier \
       --inference-specification '{"Containers":[{"Image":"763104351884.dkr.ecr.us-east-1.amazonaws.com/xgboost-inference:1.7-1-cpu-py3","ModelDataUrl":"s3://ml-models/fraud-detection/2026-08/output/model.tar.gz","Framework":"XGBOOST","FrameworkVersion":"1.7-1"}],"SupportedRealtimeInferenceInstanceTypes":["ml.m5.large","ml.m5.xlarge","ml.m5.2xlarge"],"SupportedContentTypes":["text/csv"],"SupportedResponseMIMETypes":["text/csv"]}' \
       --model-metrics '{"ModelQuality":{"Statistics":{"ContentType":"application/json","S3Uri":"s3://ml-metrics/fraud-detection/2026-08/quality.json"}},"ModelDataQuality":{"Statistics":{"ContentType":"application/json","S3Uri":"s3://ml-metrics/fraud-detection/2026-08/data-quality.json"}},"Bias":{"Report":{"ContentType":"application/json","S3Uri":"s3://ml-metrics/fraud-detection/2026-08/bias.json"}},"Explainability":{"Report":{"ContentType":"application/json","S3Uri":"s3://ml-metrics/fraud-detection/2026-08/explainability.json"}}}' \
       --approval-status PendingManualApproval
  3. aws sagemaker describe-model-package --model-package-arn <returned-arn>
POST_VERIFY:
  - [PASS] (pending execution) describe-model-package returns
    ModelPackageVersion 5, ModelApprovalStatus
    PendingManualApproval
  - [PASS] (pending execution) list-model-packages
    --model-package-group-name fraud-detection-classifier shows
    version 5
STATE: pending — will be PendingManualApproval
VERSION: 5
NOTES:
  - Versioning: group-registered; version auto-incremented to
    5. Standalone packages do not increment versions.
  - Approval: PendingManualApproval requires explicit
    update-model-package to Approved before deployment.
  - Downstream: if SageMaker Projects is wired to this group,
    the pipeline triggers only on the Approved transition (not
    on registration).
```

## What the skill caught that a generic assistant misses

1. **Group-registered vs standalone.** A generic assistant often
   omits `--model-package-group-name`, producing a standalone
   package with no versioning. The skill uses the group for
   versioning and lineage continuity.
2. **Approval status at registration.** A generic assistant
   either omits `--approval-status` (which defaults to
   PendingManualApproval but inconsistently) or sets `Approved`
   to "make it work." The skill explicitly sets
   `PendingManualApproval` for the safety gate.
3. **Artifact / image / metrics pre-flight.** A generic assistant
   registers without verifying the S3 artifact, the ECR image, or
   the metrics URIs. The skill runs `head-object` /
   `describe-images` first; a 404 would produce a dangling
   package version.
4. **Version increment.** A generic assistant does not surface
   the expected version number. The skill captures the latest
   version via `list-model-packages` and predicts version 5.
5. **Downstream pipeline caveat.** A generic assistant claims
   "registered = ready for deployment." The skill notes that
   SageMaker Projects triggers only on `Approved`, not on
   registration.

## Slash-command invocation

```
/aws:operate-sagemaker-model-registry
```

Or via the orchestrator:

```
/aws:pipeline
You: "register fraud-detection-2026-08-v1 in fraud-detection-classifier"
```

The orchestrator emits `[Phase: Operate | Skills routed:
sagemaker-model-registry-operator]` and hands off to this skill
for the VERDICT.

## Related scenarios

The same skill handles:

- **Approve for production** — `update-model-package
  --model-approval-status Approved` with an audit-trail
  `--approval-description`. Triggers SageMaker Projects pipeline.
- **Reject a model** — `update-model-package
  --model-approval-status Rejected`; blocks deployment, retains
  for audit.
- **Standalone package (no group)** — for experimentation; warn
  that no versioning lineage exists.
- **Model Card auto-population** — `create-model-card
  --source-uri <arn> --source-uri-type ModelPackage` inherits
  inference spec, metrics, approval status.
- **SageMaker Projects integration** — Project wires Model
  Registry to CodePipeline; EventBridge fires on approval
  transitions; deploy stage runs `deploy.py`.
- **Additional Inference Specifications** — multi-image packages
  (GPU + CPU variants); selectable at deploy time via
  `InferenceSpecificationName`.
- **BLOCKED: no InferenceSpecification** — approving a
  documentation-only package cannot enable deployment.
- **BLOCKED: pipeline not triggered** — verify EventBridge rule
  `EventPattern.detail.ModelPackageGroupName` matches the
  approved package's group.
