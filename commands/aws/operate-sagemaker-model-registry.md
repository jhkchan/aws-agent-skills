---
name: operate-sagemaker-model-registry
description: >-
  Slash command for the sagemaker-model-registry-operator skill.
  Operates SageMaker Model Registry lifecycles safely — creates
  model package groups; registers versioned model packages
  (model artifacts, inference images, metrics, approval
  status); drives the manual approval workflow
  (PendingManualApproval to Approved or Rejected); manages
  model package versions within a group; and distinguishes
  group-registered from standalone packages. Covers SageMaker
  Model Cards (auto-populated from packages), the Model
  Dashboard, and Model Registry with SageMaker Projects for
  CI/CD model deployment. Runs deterministic pre-checks
  (artifact accessibility, image availability, metrics S3
  reachability, IAM, approval-state legality), emits the exact
  create-model-package / update-model-package CLI behind a
  CONFIRM gate, and emits READY | BLOCKED | COMPLETED with the
  exact CLI sequence and post-verification.
skill: sagemaker-model-registry-operator
family: AI/ML
task_type: operate
verdict_shape: "READY | BLOCKED | COMPLETED"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:operate-sagemaker-model-registry

Invoke the `sagemaker-model-registry-operator` skill to plan or
execute a SageMaker Model Registry operation.

Read the skill at
`skills/sagemaker-model-registry-operator/SKILL.md` and follow its
procedure to plan and execute the operation.

## When to use

- Create a model package group (one-time per model lineage).
- Register a versioned model package (group-registered or
  standalone).
- Drive the manual approval workflow
  (`PendingManualApproval` to `Approved` or `Rejected`).
- List, describe, or delete model package versions.
- Create a SageMaker Model Card auto-populated from a registered
  package.
- Wire Model Registry with SageMaker Projects for CI/CD model
  deployment (auto-deploy on `Approved`).
- Diagnose a model package stuck in `PendingManualApproval` or a
  Projects pipeline that did not trigger on approval.
- Configure `AdditionalInferenceSpecifications` (multi-image
  packages — GPU + CPU variants).

## Invocation

```
/aws:operate-sagemaker-model-registry <group / package / approval / symptom>
```

The skill will:

1. Capture the operation target (operation type, model package
   group name, package ARN, version, approval status, region).
2. Run pre-flight: confirm group existence and `Completed`
   status, model artifact S3 accessibility, ECR image
   availability, metrics S3 reachability, IAM permissions, KMS
   decryptability, approval-state transition legality.
3. Emit the CLI sequence with all flags populated
   (`create-model-package`, `update-model-package`,
   `create-model-card`, `create-model-package-group`).
4. Verify registry state transitions via
   `describe-model-package` and `list-model-packages`.
5. On approval operations, verify the SageMaker Projects pipeline
   triggers (EventBridge → CodePipeline) when wired.
6. On `BLOCKED` (e.g., missing `InferenceSpecification`, illegal
   approval transition, pipeline not triggering), emit the root
   cause and remediation.
7. Emit the standard VERDICT block.

## Output shape

```text
OPERATION: <create-group | register-package | approve | reject | list | describe | model-card | projects-integration>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <group-name / package-arn / version, region>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command>
  2. <verify command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <PendingManualApproval | Approved | Rejected | registered>
VERSION: <ModelPackageVersion or N/A>
```

## Pre-flight

The skill requires the operation type and the model package group
name / package ARN. If only a partial configuration is provided,
the skill runs `aws sagemaker list-model-package-groups` and
`aws sagemaker list-model-packages` to surface existing resources,
or emits `BLOCKED` with the list of missing inputs for a new
operation.

## References

- Skill: `skills/sagemaker-model-registry-operator/SKILL.md`
- Reference: `skills/sagemaker-model-registry-operator/references/approval-workflow-and-cicd-pipeline.md`
- Reference: `skills/sagemaker-model-registry-operator/references/model-cards-dashboard-and-packages.md`
- AWS docs: https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry.html
