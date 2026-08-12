---
name: cloudformation-cfn-lint-operator
description: >-
  Operates CloudFormation template linting and validation with
  production defaults: cfn-lint integration (rule-based static
  analysis), template pre-deploy validation (validate-template),
  ChangeSet creation before update (exact resource change preview),
  drift detection trigger (detect-stack-drift), stack policy
  enforcement (prevent accidental resource deletion), nested stack
  validation, resource import validation, macro expansion, SAM
  transform validation (AWS::Serverless transforms), cost estimation
  (infracost integration), template security scanning (cfn-nag for
  IAM wildcard and unencrypted resources), IaC pipeline integration
  (CodePipeline + cfn-lint gate), template version control, rollback
  template archive. Emits an OPERATION_COMPLETED checklist with
  verification commands. Use when validating a CloudFormation
  template, running cfn-lint, creating a ChangeSet, detecting drift,
  scanning with cfn-nag, or linting SAM templates. Triggers: cfn
  lint, cloudformation validate template, changeset create, drift
  detection, cfn-nag security scan, sam transform validation,
  cloudformation stack policy, nested stack validation.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live operations: AWS CLI v2 with CloudFormation
  access, cfn-lint (pip install cfn-lint), cfn-nag (gem install
  cfn-nag). Works with Terraform tflint (parallel pattern) and
  CDK cdk-nag.
keywords:
  - aws
  - cloudformation
  - cfn-lint
  - cfn-nag
  - linting
  - validation
  - cloudops
  - operate
  - changeset
  - drift detection
  - stack policy
  - security scanning
  - sam
  - nested stacks
  - macro
tags:
  - aws
  - cloudformation
  - cfn-lint
  - cfn-nag
  - cloudops
  - operate
  - devtools
  - linting
  - validation
  - security
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: DevTools
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "OPERATION_COMPLETED | REVIEW_REQUIRED"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - cloudformation
    - cfn-lint
    - cfn-nag
    - cloudops
    - operate
    - devtools
    - linting
    - validation
    - security
  dependencies:
    - aws-orchestrator
  keywords:
    - cfn lint
    - cloudformation validate template
    - changeset create
    - drift detection
    - cfn nag security scan
    - sam transform validation
    - cloudformation stack policy
    - nested stack validation
  when_to_use: >-
    Invoke when the user wants to validate a CloudFormation template
    (cfn-lint, validate-template), create a ChangeSet before updating
    a stack, detect stack drift, enforce a stack policy, scan a
    template for security anti-patterns (cfn-nag), validate SAM
    transforms or nested stacks, integrate CloudFormation linting into
    a CI/CD pipeline, or archive a rollback template. Do NOT invoke
    for Terraform validation (use tflint), AWS CDK synthesis (use cdk
    synth), or general AWS resource auditing.
---

# CloudFormation cfn-lint Operator

An AWS CloudOps agent skill that operates CloudFormation template
linting and validation with correct defaults. The skill walks the
operator through cfn-lint static analysis, pre-deploy template
validation, ChangeSet creation (exact resource change preview),
drift detection, stack policy enforcement, cfn-nag security scanning,
SAM transform validation, nested stack checks, IaC pipeline
integration, and rollback template archival, captures validation
decisions, explains why each default matters, and emits an
OPERATION_COMPLETED checklist with copy-pasteable verification
commands.

## Activation keywords

cfn lint, CloudFormation validate template, changeset create, drift
detection, cfn-nag security scan, SAM transform validation,
CloudFormation stack policy, nested stack validation.

## STRICT output contract

When this skill is invoked with a CloudFormation linting or
validation request (validate a template, create a ChangeSet, detect
drift, scan with cfn-nag, validate SAM/nested stacks, or a partial
operation), the agent MUST respond with the OPERATION_COMPLETED
checklist defined in the "Output format" section using the literal
all-caps labels `CFN_LINT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
validation pipelines rely on; deviating from the literal labels
breaks automation silently.

If any issue requires human review (e.g., cfn-nag finds security
findings, drift is detected, ChangeSet shows destructive changes),
the verdict is `REVIEW_REQUIRED` with a specific issue citation in
the checklist (marked `[!]`), and `OPERATION_COMPLETED` MUST NOT
also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before operating |
| Step 1 — cfn-lint static analysis | Core linting |
| Step 2 — Pre-deploy validation (validate-template) | Syntax validation |
| Step 3 — ChangeSet creation before update | Resource change preview |
| Step 4 — Drift detection | Configuration drift |
| Step 5 — Stack policy enforcement | Resource protection |
| Step 6 — cfn-nag security scanning | Security anti-patterns |
| Step 7 — SAM transform validation | Serverless templates |
| Step 8 — Nested stack validation | Multi-stack templates |
| Step 9 — Resource import validation | Import existing resources |
| Step 10 — Macro expansion validation | Custom transforms |
| Step 11 — IaC pipeline integration (CodePipeline) | CI/CD gating |
| Step 12 — Rollback template archive | Version control |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/linting-and-validation.md | cfn-lint + validate-template detail |
| references/security-and-changesets.md | cfn-nag + ChangeSet detail |

## Mindset

**One-line takeaway:** cfn-lint catches structural and logical errors
in CloudFormation templates before deployment. validate-template
checks syntax against the CloudFormation API. ChangeSet shows the
exact resource changes an update will make. cfn-nag catches security
anti-patterns (wildcard IAM, unencrypted S3, public access). Each
tool catches a different class of issue — together they form a
defense-in-depth validation pipeline.

Three misconceptions dominate CloudFormation validation misdesign at
operation time:

- **"validate-template is enough."** It is not. `validate-template`
  checks syntax and basic resource specification compliance against
  the CloudFormation API. It does NOT catch logical errors (e.g.,
  circular dependencies, impossible conditions), security anti-
  patterns (wildcard IAM, unencrypted resources), or cost surprises.
  cfn-lint catches structural/logical issues. cfn-nag catches
  security issues. Both are needed in addition to validate-template.

- **"I can update a stack without a ChangeSet."** You can, but you
  should NOT. A ChangeSet shows the EXACT resource changes an update
  will make (Add, Modify, Remove, Replace). Without reviewing a
  ChangeSet, you may accidentally replace a resource that causes
  downtime (e.g., replacing an RDS instance with a new one because an
  immutable property changed). Always create and review a ChangeSet
  before executing it.

- **"cfn-nag is optional."** It is not. cfn-nag catches security
  anti-patterns that cfn-lint does not: wildcard IAM policies
  (`Resource: "*"`), unencrypted S3 buckets, security groups with
  `0.0.0.0/0` ingress, databases without encryption, and other
  violations of security best practices. Skipping cfn-nag means
  deploying templates with known security weaknesses.

## Configuration dependency graph (novel heuristic)

CloudFormation validation operations are NOT independent. cfn-lint
runs on the template file (no AWS API needed). validate-template
calls the CloudFormation API. ChangeSet requires an existing stack.
Drift detection requires an existing stack. Use this graph to
sequence operations.

| Operation | Hard dependencies | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| cfn-lint | Template file; cfn-lint installed | runs offline; structural/logical errors only | clean template |
| validate-template | Template file; AWS credentials | checks syntax only; NOT logic or security | syntax-valid template |
| cfn-nag | Template file; cfn-nag installed | runs offline; security anti-patterns only | security-clean template |
| ChangeSet | Stack exists; template syntax-valid | shows changes but does NOT apply; execute separately | change preview before update |
| Drift detection | Stack exists; not CREATE_IN_PROGRESS | async; results may take minutes | drift status |
| Stack policy | Stack exists; policy JSON valid | prevents UPDATE but NOT DELETE | resource protection |
| SAM transform | `Transform: AWS::Serverless`; SAM CLI | expand before linting; cfn-lint has partial SAM support | expanded template |
| Nested stacks | Parent references children; children exist | each child validated independently | validated multi-stack |
| Resource import | Stack exists; `DeletionPolicy: Retain` | not all types support import | managed resource |
| Macro expansion | Macro Lambda exists; `Transform: MacroName` | output invisible without `getTemplateSummary` | expanded template |
| Rollback archive | Template file; version control | snapshot, not live rollback | rollback capability |

**The cfn-lint-before-validate row is the one a baseline model
misses.** A naive model runs validate-template and deploys. The
correct heuristic runs cfn-lint FIRST (catches structural errors
offline, fast), then validate-template (catches API-level issues),
then cfn-nag (catches security issues), then creates a ChangeSet
(catches deployment-time issues). This sequence is the defense-in-
depth validation pipeline.

**Cross-dependency gotchas:**
- cfn-lint and validate-template catch DIFFERENT issue classes.
  cfn-lint catches structural/logical issues; validate-template
  checks syntax against the API. Both are needed.
- ChangeSet shows what WILL change but does NOT apply changes.
- SAM templates must be transformed (`sam translate`) before cfn-lint
  can fully analyze them.
- Drift detection is asynchronous — `detect-stack-drift` starts it;
  `describe-stack-drift-detection-status` returns the result.
- Stack policies prevent UPDATE but NOT DELETE operations. Use
  `DeletionPolicy: Retain` for deletion protection.

## Expert heuristic: the four-layer validation pipeline

A baseline model says "run validate-template." The correct heuristic
uses four layers, each catching a different class of issue:

```text
Layer 1: cfn-lint (offline, structural/logical)
  Catches: circular deps, invalid refs, type mismatches. Speed: seconds.

Layer 2: validate-template (API call, syntax)
  Catches: invalid properties, malformed syntax. Misses: logic, security.

Layer 3: cfn-nag (offline, security)
  Catches: wildcard IAM, unencrypted S3/RDS, public SG ingress.

Layer 4: ChangeSet (API call, deployment preview)
  Catches: resource replacement, deletion, immutable property changes.
```

**Key implication:** each layer catches what the others miss. The
full pipeline (cfn-lint → validate-template → cfn-nag → ChangeSet) is
the defense-in-depth approach.

## Expert heuristic: reading a ChangeSet

A baseline model says "create a ChangeSet." The correct heuristic
reads the ChangeSet and interprets the `Action` and `Replacement`
fields:

```text
Action: "Add" → new resource | "Modify" → update | "Remove" → delete

Replacement (for Modify):
  "True"        → REPLACED (old deleted, new created) — downtime for stateful
  "False"       → updated in place (no downtime)
  "Conditional" → replacement may or may not occur
```

**Key implication:** `Replacement: True` on a stateful resource (RDS,
EC2, EFS) means data loss unless the resource has a retention policy.
Always review `Replacement` fields before executing.

## Expert heuristic: cfn-nag finding severities

```text
CRITICAL → MUST fix before deploy (wildcard IAM, unencrypted S3, SSH from 0.0.0.0/0)
WARNING  → SHOULD review (Resource: "*", no versioning, no backup retention)
VIOLATION → Advisory (missing DeletionPolicy, no Outputs)
```

**Key implication:** CRITICAL findings block deployment (verdict:
REVIEW_REQUIRED). WARNINGs require review but may proceed with
documented justification.

## Prerequisites (verify before operating)

Before emitting operation commands, verify these prerequisites. If
any are missing, the operation cannot proceed.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Template file exists | Linting requires a local file | `ls template.yaml` |
| cfn-lint installed | Static analysis tool | `cfn-lint --version` |
| cfn-nag installed | Security scanning tool | `cfn_nag --version` |
| AWS credentials configured | validate-template and ChangeSet need API access | `aws sts get-caller-identity` |
| Stack exists (for ChangeSet/drift) | ChangeSet and drift detection operate on existing stacks | `aws cloudformation describe-stacks --stack-name <name>` |
| Stack name identified | Operations target a specific stack | Confirm stack name |
| SAM CLI installed (for SAM templates) | SAM transform expansion | `sam --version` |

If any prerequisite is missing, note it in the checklist. If
cfn-lint or cfn-nag is missing, note that security/structural
scanning is skipped (and the verdict should be REVIEW_REQUIRED if
the template has not been previously scanned).

## Step 1 — cfn-lint static analysis

cfn-lint checks templates for structural and logical errors. It runs
offline (no AWS API calls needed).

```bash
cfn-lint template.yaml                        # basic run
cfn-lint template.yaml --format json          # JSON output for pipelines
cfn-lint template.yaml --include-checks I     # include informational checks
```

**Catches:** invalid `Ref` targets, circular dependencies, invalid
property types, missing required properties, hardcoded credentials.
**Does NOT catch:** security anti-patterns (use cfn-nag), API syntax
(use validate-template), deployment issues (use ChangeSet).

## Step 2 — Pre-deploy validation (validate-template)

`validate-template` calls the CloudFormation API to check syntax and
resource property compliance.

```bash
aws cloudformation validate-template --template-body file://template.yaml --region us-east-1
```

**Catches:** malformed YAML/JSON, invalid resource type names,
invalid property names, template size violations (max 460,800 bytes).
**Does NOT catch:** logical errors, security anti-patterns, resource
replacement/deletion.

**Common mistake:** relying on validate-template alone. Always pair
with cfn-lint (structural) and cfn-nag (security).

## Step 3 — ChangeSet creation before update

A ChangeSet shows the EXACT resource changes an update will make.
Create, review, then execute (or delete if changes are unexpected).

```bash
CHANGESET_NAME="update-$(date +%Y%m%d%H%M%S)"
aws cloudformation create-change-set --stack-name my-stack \
  --change-set-name "$CHANGESET_NAME" --template-body file://template-updated.yaml \
  --capabilities CAPABILITY_NAMED_IAM --region us-east-1

aws cloudformation wait change-set-create-complete --change-set-name "$CHANGESET_NAME" --stack-name my-stack --region us-east-1

aws cloudformation describe-change-set --change-set-name "$CHANGESET_NAME" --stack-name my-stack \
  --query 'Changes[*].{Action:ResourceChange.Action,Resource:ResourceChange.LogicalResourceId,Replacement:ResourceChange.Replacement}' \
  --region us-east-1 --output table
```

| Action | Replacement | Risk |
|---|---|---|
| Add | N/A | Low — safe to execute |
| Modify | False | Low — in-place update |
| Modify | Conditional | Medium — review changed properties |
| Modify | True | HIGH — resource replaced (downtime/data loss risk) |
| Remove | N/A | HIGH — resource deleted |

```bash
aws cloudformation execute-change-set --change-set-name "$CHANGESET_NAME" --stack-name my-stack --region us-east-1
# Or delete if unacceptable:
aws cloudformation delete-change-set --change-set-name "$CHANGESET_NAME" --stack-name my-stack --region us-east-1
```

## Step 4 — Drift detection

Drift detection checks whether the stack's actual configuration
differs from the template.

```bash
DETECTION_ID=$(aws cloudformation detect-stack-drift --stack-name my-stack \
  --query 'StackDriftDetectionId' --output text --region us-east-1)
aws cloudformation describe-stack-drift-detection-status --stack-drift-detection-id "$DETECTION_ID" --region us-east-1
aws cloudformation describe-stack-resource-drifts --stack-name my-stack \
  --stack-resource-drift-status-filters MODIFIED DELETED --region us-east-1 --output table
```

`IN_SYNC` = no drift. `DRIFTED` = resources modified outside
CloudFormation (console, CLI, Auto Scaling). Review and reconcile.

## Step 5 — Stack policy enforcement

A stack policy prevents accidental updates to specific resources.

```bash
aws cloudformation set-stack-policy --stack-name my-stack --stack-policy-body file://stack-policy.json --region us-east-1
```

```json
{
  "Statement": [
    { "Effect": "Deny", "Action": "Update:*", "Principal": "*", "Resource": "*",
      "Condition": { "StringEquals": { "ResourceType": ["AWS::RDS::DBInstance", "AWS::S3::Bucket"] } } },
    { "Effect": "Allow", "Action": "Update:*", "Principal": "*", "Resource": "*" }
  ]
}
```

**Critical:** stack policies prevent UPDATE but NOT DELETE. Use
`DeletionPolicy: Retain` for deletion protection.

## Step 6 — cfn-nag security scanning

cfn-nag scans templates for security anti-patterns. Runs offline.

```bash
cfn_nag_scan --input-path template.yaml
cfn_nag_scan --input-path template.yaml --output-format json
```

**Common CRITICAL findings:** IAM `Resource: "*"` (F1), IAM
`Action: "*"` (F2), S3 without encryption (W41), SG ingress
`0.0.0.0/0` to SSH port 22 (F1000), RDS public access (W40), RDS
without encryption (W73).

CRITICAL findings set verdict to REVIEW_REQUIRED. Suppress false
positives via metadata:

```yaml
MyBucket:
  Type: AWS::S3::Bucket
  Metadata:
    cfn_nag:
      rules_to_suppress:
        - id: W41
          reason: "Log bucket — encryption at org level"
```

## Step 7 — SAM transform validation

SAM templates use `Transform: AWS::Serverless-2016-10-31`. Always
expand before linting for full coverage.

```bash
sam translate --template-file template-sam.yaml --output-file template-expanded.yaml
cfn-lint template-expanded.yaml
cfn_nag_scan --input-path template-expanded.yaml
aws cloudformation validate-template --template-body file://template-expanded.yaml --region us-east-1
```

**Common SAM issues:** missing `CodeUri`/`InlineCode`, deprecated
`Runtime`, missing `Handler`, invalid `Globals` properties.

## Step 8 — Nested stack validation

Each child template must be linted independently — parent-level
cfn-lint does NOT recurse into nested stacks.

```bash
# Validate the parent template
cfn-lint parent-template.yaml
aws cloudformation validate-template \
  --template-body file://parent-template.yaml \
  --region us-east-1

# Validate each child template
cfn-lint child-network.yaml
cfn-lint child-database.yaml
cfn-lint child-application.yaml

# Validate each child with validate-template
aws cloudformation validate-template --template-body file://child-network.yaml --region us-east-1
aws cloudformation validate-template --template-body file://child-database.yaml --region us-east-1
aws cloudformation validate-template --template-body file://child-application.yaml --region us-east-1
```

**Common nested stack issues:**
- Parent passes parameters that the child template does not expect.
- Parent expects outputs that the child does not export.
- Child template URL points to a non-existent S3 object.
- Circular dependencies between nested stacks (not allowed).

## Step 9 — Resource import and macro validation

**Resource import** brings existing AWS resources under CloudFormation
management. Each imported resource MUST have `DeletionPolicy: Retain`.
Not all resource types support import — check the support matrix.
Drift detection runs during import.

```bash
aws cloudformation create-change-set \
  --stack-name my-stack --change-set-name import-cs \
  --change-set-type IMPORT \
  --template-body file://template-import.yaml \
  --resources-to-import file://resources.json --region us-east-1
```

**Macro expansion:** macros transform template content via Lambda at
deployment time. cfn-lint and validate-template see the PRE-macro
template. Use `get-template-summary` to inspect the expanded output.

```bash
aws cloudformation get-template-summary \
  --template-body file://template-with-macro.yaml --region us-east-1
```

## Step 10 — IaC pipeline integration (CodePipeline + cfn-lint)

Integrate validation into a CodePipeline CI/CD pipeline as a quality
gate. The pipeline runs cfn-lint, cfn-nag, and creates a ChangeSet
before manual approval and execution.

**Pipeline gating logic:**
1. cfn-lint must pass (no errors).
2. cfn-nag must pass (no CRITICAL findings).
3. ChangeSet must be created (review required for replacements).
4. Execute ChangeSet only after manual approval.

```yaml
# CodePipeline Build stage with cfn-lint and cfn-nag gates
- Name: ValidateTemplate
  Actions:
    - Name: cfnLint
      ActionTypeId: { Category: Build, Owner: AWS, Provider: CodeBuild, Version: "1" }
      Configuration: { ProjectName: cfn-lint-project }
      RunOrder: 1
    - Name: cfnNag
      ActionTypeId: { Category: Build, Owner: AWS, Provider: CodeBuild, Version: "1" }
      Configuration: { ProjectName: cfn-nag-project }
      RunOrder: 2
    - Name: createChangeSet
      ActionTypeId: { Category: Deploy, Owner: AWS, Provider: CloudFormation, Version: "1" }
      Configuration:
        ActionMode: CHANGE_SET_REPLACE
        StackName: !Ref StackName
        ChangeSetName: pipeline-changeset
        Capabilities: CAPABILITY_NAMED_IAM
      RunOrder: 3
```

## Step 11 — Rollback template archive

Archive the current template before deploying a new version. This
enables rollback by deploying the archived template.

```bash
# Archive the current template to versioned S3
aws cloudformation get-template --stack-name my-stack \
  --query 'TemplateBody' --region us-east-1 > "template-$(date +%Y%m%d%H%M%S).yaml"
aws s3 cp "template-$(date +%Y%m%d%H%M%S).yaml" s3://my-cfn-archive/templates/ --region us-east-1

# To roll back: deploy the archived template
aws cloudformation update-stack --stack-name my-stack \
  --template-body file://template-previous.yaml --region us-east-1
```

## Step 13 — Recent features

**Recent AWS features (2023-2026):**

- **cfn-lint enhanced resource specification coverage (2023-2024):**
  cfn-lint now covers all AWS resource specifications including
  newer services (AppRunner, Bedrock, Security Hub). Rules are
  auto-generated from the AWS resource specification JSON.

- **CloudFormation Hooks (2023-2024):** Hooks allow pre-deployment
  and post-deployment evaluation of template changes. Hooks run
  BEFORE a ChangeSet is executed, enabling proactive policy
  enforcement (e.g., block templates with unencrypted resources).

- **cfn-nag improved IAM analysis (2023-2024):** Enhanced IAM policy
  analysis in cfn-nag, including detection of privilege escalation
  patterns, unused IAM actions, and cross-account trust
  relationships.

- **Drift detection improvements (2023-2024):** Extended drift
  detection support to additional resource types (including
  CloudFront distributions, API Gateway REST APIs, and AppSync
  APIs). Previously, many resource types were not supported by drift
  detection.

- **ChangeSet nested stack visibility (2024-2025):** ChangeSet now
  shows changes within nested stacks, not just the parent stack.
  Previously, nested stack changes were opaque in the ChangeSet
  view.

- **SAM CLI cfn-lint integration (2024-2025):** The SAM CLI now
  integrates cfn-lint directly, running lint checks during
  `sam build` and `sam deploy` without requiring a separate cfn-lint
  invocation.

## NEVER do these things

1. **NEVER rely on validate-template alone.** validate-template
   checks syntax but NOT logic or security. Always pair with
   cfn-lint (structural) and cfn-nag (security).

2. **NEVER update a stack without reviewing the ChangeSet.** The
   ChangeSet shows exactly what will change. Without reviewing it,
   you may accidentally replace or delete resources, causing
   downtime or data loss.

3. **NEVER ignore cfn-nag CRITICAL findings.** CRITICAL findings
   (wildcard IAM, unencrypted resources, public access) are security
   vulnerabilities. Resolve them before deployment or suppress with
   documented justification.

4. **NEVER confuse Replacement: True with Replacement: False.**
   `Replacement: True` means the resource is deleted and recreated.
   For stateful resources (RDS, EC2, EFS), this causes data loss
   unless there is a backup and retention policy.

5. **NEVER assume stack policies prevent deletion.** Stack policies
   only prevent UPDATE operations. Stack deletion ignores policies.
   Use `DeletionPolicy: Retain` for deletion protection.

6. **NEVER skip drift detection before updating.** If a stack has
   drifted (out-of-band changes), updating from the template may
   overwrite manual changes. Always detect drift before updating.

7. **NEVER lint only the parent template for nested stacks.** Each
   child template must be linted independently. Parent-level cfn-lint
   does NOT recurse into nested stack templates.

8. **NEVER deploy SAM templates without expanding the transform.**
   cfn-lint has partial SAM support. Always expand with `sam
   translate` first, then lint the expanded CloudFormation template.

9. **NEVER ignore macro-expanded content.** Macros transform template
   content at deployment time. The pre-macro template may pass cfn-
   lint, but the post-macro output may be invalid. Use
   `get-template-summary` to inspect the expanded template.

10. **NEVER forget to archive the template before updating.** Always
    archive the current template (via `get-template` to S3) before
    deploying a new version. This enables rollback if the update
    fails or causes issues.

## Output format

```text
CFN_LINT: <template-file> → <stack-name>
VERDICT: OPERATION_COMPLETED | REVIEW_REQUIRED
CHECKLIST:
  [✓|✗] Template file: <file>
  [✓|!] cfn-lint: PASSED (<errors> errors, <warnings> warnings) | FAILED (<count> errors)
  [✓|!] validate-template: PASSED | FAILED (<issue>)
  [✓|!] cfn-nag: PASSED (<critical> critical, <warnings> warnings) | CRITICAL FINDINGS (<count>)
  [✓|!] ChangeSet: <change-set-name> — <add> Add, <modify> Modify, <remove> Remove | REPLACEMENT REQUIRED
  [✓|!] Drift detection: IN_SYNC | DRIFTED (<count> resources drifted)
  [✓|!] Stack policy: Enforced (<protected-resource-types>) | Not set
  [✓|!] SAM transform: Expanded and validated | N/A (not a SAM template)
  [✓|!] Nested stacks: Validated (<count> child templates) | N/A (no nested stacks)
  [✓|!] Rollback archive: Archived to <s3-uri> | Not archived
  [✓|!] Pipeline gate: cfn-lint + cfn-nag + ChangeSet review | Not integrated
  [✓] Tags: <key=value list>
VERIFICATION_COMMANDS:
  cfn-lint <template-file>
  cfn_nag_scan --input-path <template-file>
  aws cloudformation describe-change-set --change-set-name <change-set-name> --stack-name <stack-name> --region <region>
```

### Worked example — template validation with cfn-lint, cfn-nag, and ChangeSet

```text
CFN_LINT: template.yaml → my-app-stack
VERDICT: OPERATION_COMPLETED
CHECKLIST:
  [✓] Template file: template.yaml
  [✓] cfn-lint: PASSED (0 errors, 2 warnings)
  [✓] validate-template: PASSED
  [✓] cfn-nag: PASSED (0 critical, 3 warnings)
  [✓] ChangeSet: update-20260805 — 1 Add, 2 Modify, 0 Remove
  [✓] Drift detection: IN_SYNC
  [✓] Stack policy: Enforced (AWS::RDS::DBInstance, AWS::S3::Bucket)
  [✓] SAM transform: N/A (not a SAM template)
  [✓] Nested stacks: N/A (no nested stacks)
  [✓] Rollback archive: Archived to s3://my-cfn-archive/templates/template-20260805.yaml
  [✓] Pipeline gate: cfn-lint + cfn-nag + ChangeSet review
  [✓] Tags: Environment=production, Application=my-app
VERIFICATION_COMMANDS:
  cfn-lint template.yaml
  cfn_nag_scan --input-path template.yaml
  aws cloudformation describe-change-set --change-set-name update-20260805 --stack-name my-app-stack --region us-east-1
```

### Worked example — cfn-nag finds CRITICAL findings (REVIEW_REQUIRED)

```text
CFN_LINT: template.yaml → my-app-stack
VERDICT: REVIEW_REQUIRED
CHECKLIST:
  [✓] Template file: template.yaml
  [✓] cfn-lint: PASSED (0 errors, 1 warning)
  [✓] validate-template: PASSED
  [!] cfn-nag: CRITICAL FINDINGS (2) — F1: IAM policy with Resource "*" in role TaskExecutionRole; F1000: Security group ingress from 0.0.0.0/0 to port 22
  [✓] ChangeSet: Not created (blocked by cfn-nag findings)
  [✓] Drift detection: IN_SYNC
  [✓] Stack policy: Not set
VERIFICATION_COMMANDS:
  cfn-lint template.yaml
  cfn_nag_scan --input-path template.yaml
```

## Error handling

### cfn-lint fails with errors
- Fix structural/logical errors: correct `Ref` targets, resolve
  circular dependencies, add missing required properties.

### validate-template fails
- Invalid syntax or resource properties. Fix the template structure.
  Check the AWS resource specification for correct property names.

### cfn-nag finds CRITICAL findings
- Fix security anti-patterns: scope IAM policies, add encryption,
  restrict ingress. Suppress false positives with justification.

### ChangeSet shows unexpected Replacement: True
- An immutable property changed. Review the changed property. If
  unintentional, revert the change before executing the ChangeSet.

### Drift detection shows DRIFTED
- Resources modified outside CloudFormation. Update the template to
  match actual configuration, or revert out-of-band changes.

### Stack deployment fails (rollback)
- CloudFormation auto-rolls back to the previous known-good state.
  Review `describe-stack-events` for the cause. Fix and retry.

## Domain

AWS CloudOps / CloudFormation Template Linting, Validation, and
Security Scanning Operations.

## AWS documentation

- **CloudFormation User Guide** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html
- **validate-template** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-validate-template.html
- **ChangeSets** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html
- **Drift detection** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html
- **Stack policies** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/protect-stack-resources.html
- **Resource import** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resource-import.html
- **Macros** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-macros.html
- **cfn-lint (GitHub)** — https://github.com/aws-cloudformation/cfn-lint
- **cfn-nag (GitHub)** — https://github.com/stelligent/cfn_nag
- **SAM CLI** — https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html
