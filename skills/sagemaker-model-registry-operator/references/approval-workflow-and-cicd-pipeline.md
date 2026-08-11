# Approval workflow and CI/CD pipeline — deep reference

This reference expands the SKILL.md approval workflow and
SageMaker Projects CI/CD integration. Load when wiring an approval
workflow, configuring SageMaker Projects for auto-deploy, or
diagnosing a pipeline that did not trigger on approval.

## Approval state machine (full detail)

### States and transitions

```
                       create-model-package
                              │
                              ▼
                  ┌───────────────────────┐
                  │ PendingManualApproval │  ◄──── default for
                  │   (or AutoApproved    │       manual-approval
                  │    if group is auto)  │       groups
                  └───────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        ┌──────────┐    ┌──────────┐    (no transition;
        │ Approved │    │ Rejected │     stays pending)
        └────┬─────┘    └────┬─────┘
             │               │
             │ (rollback)    │ (rare reversal)
             ▼               ▼
        ┌──────────┐    ┌──────────┐
        │ Rejected │    │ Approved │
        └──────────┘    └──────────┘
```

### Auto-approval vs manual approval

The group-level setting `ModelApprovalMode` (2024-2026) controls
the default:

| Mode | Default for new packages | Use case |
|---|---|---|
| `ManualApproval` (default) | `PendingManualApproval` | Production — human review required |
| `AutoApproval` | `AutoApproved` | Dev / sandbox — skip review |

Even in `AutoApproval` mode, the operator can override at
registration time with `--approval-status PendingManualApproval`
to force review.

### Approval descriptions

Always include an `--approval-description` on
`update-model-package`. The description is the audit trail for
why the package was approved or rejected. Capture:

- The reviewer (name, role).
- The metrics reviewed (AUC, precision, recall, bias, drift).
- The decision rationale.
- The ticket / change-request reference.

## EventBridge events on approval

### Event pattern

`update-model-package` transitioning to `Approved` or `Rejected`
emits an EventBridge event:

```json
{
  "version": "0",
  "id": "abc-123",
  "detail-type": "SageMaker Model Package State Change",
  "source": "aws.sagemaker",
  "account": "111122223333",
  "region": "us-east-1",
  "detail": {
    "ModelPackageGroupName": "fraud-detection-classifier",
    "ModelPackageVersion": 5,
    "ModelApprovalStatus": "Approved",
    "ModelPackageArn": "arn:aws:sagemaker:us-east-1:111122223333:model-package/fraud-detection-classifier/5"
  }
}
```

### Wiring a downstream rule

```bash
aws events put-rule \
  --name "fraud-detection-approved" \
  --event-pattern '{
    "source": ["aws.sagemaker"],
    "detail-type": ["SageMaker Model Package State Change"],
    "detail": {
      "ModelPackageGroupName": ["fraud-detection-classifier"],
      "ModelApprovalStatus": ["Approved"]
    }
  }'

aws events put-targets \
  --rule "fraud-detection-approved" \
  --targets '{"Id":"1","Arn":"arn:aws:codepipeline:us-east-1:111122223333:fraud-detection-deploy"}'
```

The CodePipeline consumes the event as a source and triggers the
deploy stage.

## SageMaker Projects deployment templates

### Available MLOps templates (2026)

| Template | What it provisions | When to use |
|---|---|---|
| `MLOps template for model deployment` | CodePipeline (deploy stage only); consumes Approved packages | Model building happens outside the project |
| `MLOps template for model building and training` | CodePipeline (build + train + register stages) | Full training-to-registry pipeline |
| `MLOps template for model building, training, and deployment` | CodePipeline (build + train + register + deploy) | End-to-end MLOps |
| `MLOps template for model bias drift` | CodePipeline with bias monitoring + re-training | Production monitoring with auto-retrain |

Each template creates:
- A SageMaker Project (Service Catalog product).
- One or more CodePipeline pipelines.
- CodeBuild / CodeCommit / CodeDeploy resources as needed.
- EventBridge rules wiring approval events to the pipeline.
- IAM roles for the pipeline stages.

### Project structure

```
sagemaker-project/
├── Pipelines/
│   └── deploy_pipeline.py     # SageMaker Pipelines definition
├── build/
│   └── buildspec.yml          # CodeBuild build spec
├── deploy/
│   ├── buildspec.yml          # CodeBuild deploy spec
│   └── deploy.py              # creates model, endpoint-config, endpoint
└── .sagemaker-pipelines/      # pipeline metadata
```

The deploy stage's `deploy.py` reads the approved model package
ARN from the EventBridge event payload and creates a SageMaker
model referencing the package's `InferenceSpecification`.

### Verifying project wiring

```bash
# Confirm the project exists and its provisioning status:
aws sagemaker describe-project --project-name "fraud-detection-deploy" \
  --query '{status:ProjectStatus,id:ProjectId,product:Provisioning.ProvisionedProductProvisioningArtifactId}'

# List pipelines associated with the project:
aws codepipeline list-pipelines --query 'pipelines[?contains(name, `fraud-detection`)].[name]'

# Check the EventBridge rules targeting the pipeline:
aws events list-rule-names-by-target --target-arn arn:aws:codepipeline:us-east-1:111122223333:fraud-detection-deploy

# List recent pipeline executions:
aws codepipeline list-pipeline-executions --pipeline-name "fraud-detection-deploy" \
  --query 'pipelineExecutionSummaries[*].{status:status,startTime:startTime,sourceRevisions:sourceRevisions}'
```

## Multi-environment deployment patterns

### Pattern: Dev → Staging → Prod via separate groups

Maintain a separate model package group per environment:

- `fraud-detection-dev` — auto-approval; rapid iteration.
- `fraud-detection-staging` — manual approval; integration tests.
- `fraud-detection-prod` — manual approval; production SLA.

Promote a model by re-registering the same artifact in the next
group. Use `CustomerMetadataProperties` to track the source
version:

```bash
aws sagemaker update-model-package \
  --model-package-arn arn:aws:sagemaker:us-east-1:111122223333:model-package/fraud-detection-prod/12 \
  --customer-metadata-properties '{"promoted-from":"fraud-detection-staging/8","promoted-by":"risk-platform","promotion-date":"2026-08-11"}
```

### Pattern: Single group with environment tags

Use one group, tag packages with environment:

- `fraud-detection-classifier` group, packages tagged
  `environment=dev | staging | prod`.

The CI/CD pipeline filters by tag. Less isolation but simpler
lineage tracking.

### Pattern: Blue/green via endpoint variants

A package approved for prod can be deployed as a blue/green
variant on the SageMaker endpoint. The endpoint config defines
two variants (e.g., `variant-1` at 100%, `variant-2` at 0%);
`update-endpoint-weights-and-capacities` shifts traffic.

The Model Registry approval gates which package version becomes
`variant-2`. Approve version N+1, deploy as `variant-2` at 0%,
shift traffic, then promote `variant-2` to `variant-1` once
healthy.

## Diagnostic runbooks

### Pipeline did not trigger on approval

1. `describe-model-package` — confirm `ModelApprovalStatus:
   Approved` and the timestamp.
2. `events list-rules` — find the rule for the pipeline. Verify
   the `EventPattern.detail.ModelPackageGroupName` matches the
   approved package's group.
3. `events test-event-pattern` — replay the approval event and
   confirm the rule matches.
4. `codepipeline list-pipeline-executions` — check whether the
   pipeline has a recent execution.
5. If the rule matches but no execution: the pipeline's source
   stage may be mis-configured. Check the pipeline definition.

### Pipeline deploy stage failed

1. `codepipeline get-pipeline-execution --pipeline-name <name> --pipeline-execution-id <id>` — capture the failed stage.
2. `codepipeline list-action-executions --pipeline-name <name>` —
   find the failed action and its external execution ID.
3. For CodeBuild actions: `codebuild batch-get-builds --ids <id>`
   — read the build logs.
4. Common failure causes:
   - IAM: pipeline role lacks `sagemaker:CreateModel` or
     `iam:PassRole` on the execution role.
   - Resource conflict: endpoint already exists with a different
     config.
   - Model artifact inaccessible: the pipeline role lacks
     `s3:GetObject` on the artifact bucket.
   - KMS: pipeline role lacks `kms:Decrypt` on the model
     artifact KMS key.

### Approved package but endpoint still serving old version

1. `describe-model-package` — confirm `Approved`.
2. `sagemaker describe-endpoint --endpoint-name <name>` —
   capture `ProductionVariants[].ModelName`.
3. `sagemaker describe-model --model-name <name>` — capture
   `PrimaryContainer.ModelDataUrl` (the artifact).
4. Compare the deployed artifact with the approved package's
   artifact. If different, the pipeline did not deploy the new
   version.
5. Manually trigger `update-endpoint` or `create-model` +
   `create-endpoint-config` + `update-endpoint` to deploy the
   approved version.

### Rejected package accidentally deployed

1. `describe-model-package` — confirm the package is `Rejected`.
2. Check the endpoint's deployed model — if it matches the
   rejected artifact, the deployment happened before the
   rejection.
3. Revert: trigger the pipeline to deploy the prior `Approved`
   version. If no prior `Approved` exists, re-register the last
   known-good artifact, approve it, and trigger the pipeline.
