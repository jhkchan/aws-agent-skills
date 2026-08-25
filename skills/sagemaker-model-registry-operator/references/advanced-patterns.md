# Advanced Patterns — SageMaker Model Registry Operator

Expert-knowledge deep dives, heuristics, and recent-feature notes moved out of the SKILL.md body. Loaded on demand.


## Step 0: Expert knowledge — non-obvious Model Registry behaviors

- **Group-registered vs standalone packages are fundamentally different.**
  A group-registered package (`ModelPackageGroupName` set on
  `create-model-package`) gets an auto-incremented
  `ModelPackageVersion` and appears in
  `list-model-packages --model-package-group-name <group>`. A
  standalone package (no group) is one-off — it has a unique
  name but no version lineage. Production registries always use
  groups.

- **Approval status is set at registration time, not auto-defaulted.**
  `create-model-package` accepts `--approval-status`. If omitted
  on a group-registered package, the default is
  `PendingManualApproval`. Setting `Approved` at registration
  bypasses review — use only for dev / sandbox or auto-approval
  groups.

- **`update-model-package` is the only way to change approval status post-registration.**
  `update-model-package --model-package-arn <arn>
  --model-approval-status Approved` transitions the package.
  There is no `approve-model-package` API — the same call
  handles approve, reject, and rollback.

- **A registered package is immutable.** Once
  `create-model-package` returns success, the package's
  `InferenceSpecification`, `ModelArtifact`, and `SourceAlgorithm`
  cannot be modified. To change any of these, register a new
  version. Only `ModelApprovalStatus`, `Description`, `Tags`,
  `CustomerMetadataProperties`, and (in 2024-2026) some
  `AdditionalInferenceSpecifications` are mutable.

- **Model Cards can auto-populate from a registered package.**
  `create-model-card --source-uri <model-package-arn>` (with
  `--source-uri-type ModelPackage`) pulls the inference spec,
  metrics, and approval status into the card automatically.
  Without a registered package source, the card must be
  authored manually.

- **SageMaker Projects wires Model Registry to CI/CD.** A
  SageMaker Project (created from the
  `MLOps template for model deployment` or
  `MLOps template for model building, training, and deployment`)
  provisions a CodePipeline that auto-deploys approved model
  packages from a designated group to a SageMaker endpoint.
  EventBridge fires on `Approved` transitions; the pipeline
  consumes the event and runs the deploy stage.

- **`AdditionalInferenceSpecifications` enables multi-image packages.**
  A package can declare multiple inference specs (e.g., GPU and
  CPU variants, or TensorFlow and PyTorch serving images). The
  primary `InferenceSpecification` is used by default;
  `AdditionalInferenceSpecifications` are selectable at deploy
  time via the `InferenceSpecificationName` parameter.

- **`SourceAlgorithmSpecification` is required for algorithm-marketplace packages.**
  Packages derived from an AWS Marketplace algorithm must set
  `SourceAlgorithms[].AlgorithmName` to the Marketplace
  algorithm ARN. Without this, the package cannot be listed or
  deployed via Marketplace.

- **`ModelPackageArn` is the canonical identifier.** The
  `ModelPackageName` is unique within the account-region, but
  downstream services (SageMaker Projects, Model Cards,
  EventBridge) reference the package by ARN. Always capture and
  propagate the ARN.

- **`ValidationSpecification` runs pre-registration checks.**
  `create-model-package` accepts a `ValidationSpecification`
  with validation profiles (instance type, instance count,
  batch transform input). SageMaker runs the validation jobs
  before registering the package; failures leave the package
  un-registered. Use for automated quality gates.

- **KMS encryption on the registry does not re-encrypt model artifacts.**
  `ModelPackageGroup.KmsKeyId` encrypts the registry metadata.
  The model artifacts (`model.tar.gz` in S3) remain encrypted
  with whatever key was used at training time. The deployer
  role must have `kms:Decrypt` on both keys.

- **A rejected package is not deleted.** `ModelApprovalStatus:
  Rejected` blocks deployment but the package version remains
  in the registry for audit. To remove a package entirely, use
  `delete-model-package`. The version number is not reused.

## Expert heuristic: "Approval is a deployment gate, not a label"

`ModelApprovalStatus` is the gate that downstream CI/CD
(SageMaker Projects, EventBridge) checks before deploying a model
package to a SageMaker endpoint.

```
Registration lifecycle
   ├─ create-model-package (InferenceSpecification + ModelMetrics + PendingManualApproval)
   │    └─ Model package version N in group
   │         ├─ Reviewer evaluates metrics (AUC, precision, bias, drift)
   │         ├─ update-model-package --model-approval-status Approved
   │         │    └─ EventBridge fires "SageMaker Model Package State Change"
   │         │         └─ SageMaker Projects pipeline triggers deploy stage
   │         │              └─ Endpoint updated to version N
   │         └─ update-model-package --model-approval-status Rejected
   │              └─ Package version N blocked; deployment not triggered
   │                   └─ Re-train, register version N+1
```

**Approval-state transition matrix:**

| From | To | Effect |
|---|---|---|
| `PendingManualApproval` | `Approved` | Triggers downstream deploy |
| `PendingManualApproval` | `Rejected` | Blocks deploy; package retained for audit |
| `Approved` | `Rejected` | Does NOT auto-rollback deployed endpoint — pipeline must re-deploy prior version |
| `Rejected` | `Approved` | Unusual; ensure the metrics support the reversal |

**Group vs standalone decision:**

| Pattern | Versioning | Use case |
|---|---|---|
| Group-registered (`ModelPackageGroupName` set) | Auto-incremented `ModelPackageVersion` | Production lineage — always use |
| Standalone (no group) | No versioning | Experimentation, one-off, throw-away |

**Per-operation pre-checks:**

| Operation | What to verify |
|---|---|
| `create-group` | Name uniqueness, KMS key enabled |
| `register-package` (group) | Group exists and Completed; artifact, image, metrics reachable |
| `register-package` (standalone) | Warn no versioning; otherwise same as group |
| `approve` | Current state allows transition; package has InferenceSpecification |
| `reject` | Current state allows transition |
| `model-card` | Source package exists (if `--source-uri-type ModelPackage`) |
| `projects-integration` | Project exists; pipeline role has deploy permissions; group has at least one Approved version |

## Recent AWS features (2024-2026)

- **SageMaker Model Cards (2024-2026):**
  `create-model-card --source-uri <arn> --source-uri-type
  ModelPackage` auto-populates the card from the registered
  package (inference spec, metrics, approval status). Cards
  support `Draft`, `PendingReview`, `Approved` states and are
  visible in SageMaker Studio and the Model Dashboard.
- **SageMaker Model Dashboard (2024-2026):**
  unified console view across Model Registry packages, Model
  Cards, endpoints, and training jobs. Cross-registry filtering
  by approval status, group, tags. Integrates with MLflow
  Tracking via `list-mlflow-models`.
- **Model Registry with SageMaker Projects (2024-2026):**
  Projects created from the `MLOps template for model
  deployment` provision a CodePipeline that auto-deploys
  `Approved` packages from a designated group to a SageMaker
  endpoint. EventBridge fires on the approval transition.
- **Additional Inference Specifications (2024-2026):**
  enables multi-image packages (GPU and CPU variants). The
  primary spec is default; additional specs are selectable at
  deploy time via `InferenceSpecificationName`.
- **Model Registry KMS encryption (2024-2025):** `KmsKeyId`
  on the group encrypts registry metadata; artifacts in S3
  keep the training KMS key. Deployer roles need
  `kms:Decrypt` on both.
- **Model package validation (2024-2025):**
  `ValidationSpecification` runs batch-transform validation
  jobs before registering the package — automated quality gate.
- **Customer Metadata Properties (2024-2025):** mutable
  key-value metadata on registered packages (e.g., link to
  the JIRA approval ticket).
- **Model Registry + MLflow (2024-2026):** integrated lineage
  view linking MLflow runs to package versions via
  `CustomerMetadataProperties`.
- **EventBridge model package state change (2024-2026):**
  events fire on approval transitions, registration, deletion.
  Downstream consumers (Projects pipelines, Lambda, SNS)
  subscribe.
- **Model Dashboard cross-account / cross-region (2025-2026):**
  aggregates packages across accounts and regions via
  SageMaker Studio cross-account configurations.
