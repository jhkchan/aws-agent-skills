# End-to-End Example: CloudFormation cfn-lint Validation Pipeline

A walkthrough showing how to use the `cloudformation-cfn-lint-
operator` skill from invocation through the four-layer validation
pipeline. Mirrors the structured-eval pattern of shipping a concrete
worked example per skill.

---

## Scenario

You are validating a CloudFormation template before deploying an
update to a production stack. The validation needs:

- Template file: template.yaml
- Stack name: my-app-stack
- Region: us-east-1
- Stack policy: protect RDS and S3 resources
- Full pipeline: cfn-lint, validate-template, cfn-nag, ChangeSet

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:operate-cfn-lint
```

Then paste the requirements.

### Option B: Natural language

```
You: "Validate my CloudFormation template.yaml for stack
      my-app-stack in us-east-1. Run cfn-lint, validate-template,
      cfn-nag, and create a ChangeSet."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "cfn lint cloudformation template"
```

---

## Step 2 — Skill produces the OPERATION_COMPLETED checklist

```text
CFN_LINT: template.yaml → my-app-stack
VERDICT: OPERATION_COMPLETED
CHECKLIST:
  [✓] Template file: template.yaml
  [✓] cfn-lint: PASSED (0 errors, 2 warnings)
  [✓] validate-template: PASSED
  [✓] cfn-nag: PASSED (0 critical, 1 warning)
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

---

## Step 3 — Run the four-layer validation pipeline

```bash
# Layer 1: cfn-lint (offline structural/logical check)
cfn-lint template.yaml --format json
# Expected: 0 errors

# Layer 2: validate-template (API syntax check)
aws cloudformation validate-template \
  --template-body file://template.yaml \
  --region us-east-1
# Expected: no error

# Layer 3: cfn-nag (offline security scan)
cfn_nag_scan --input-path template.yaml
# Expected: 0 critical findings

# Layer 4: ChangeSet (deployment preview)
CHANGESET_NAME="update-$(date +%Y%m%d%H%M%S)"
aws cloudformation create-change-set \
  --stack-name my-app-stack \
  --change-set-name "$CHANGESET_NAME" \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

aws cloudformation wait change-set-create-complete \
  --change-set-name "$CHANGESET_NAME" \
  --stack-name my-app-stack \
  --region us-east-1

aws cloudformation describe-change-set \
  --change-set-name "$CHANGESET_NAME" \
  --stack-name my-app-stack \
  --query 'Changes[*].{Action:ResourceChange.Action,Resource:ResourceChange.LogicalResourceId,Replacement:ResourceChange.Replacement}' \
  --region us-east-1 --output table
```

---

## Step 4 — Drift detection and stack policy

```bash
# Drift detection
DETECTION_ID=$(aws cloudformation detect-stack-drift \
  --stack-name my-app-stack \
  --query 'StackDriftDetectionId' --output text --region us-east-1)

aws cloudformation describe-stack-resource-drifts \
  --stack-name my-app-stack \
  --region us-east-1 --output table
# Expected: IN_SYNC

# Stack policy
aws cloudformation set-stack-policy \
  --stack-name my-app-stack \
  --stack-policy-body file://stack-policy.json \
  --region us-east-1
```

---

## Step 5 — Archive template and execute ChangeSet

```bash
# Archive current template for rollback
aws cloudformation get-template --stack-name my-app-stack \
  --query 'TemplateBody' --region us-east-1 > "template-$(date +%Y%m%d%H%M%S).yaml"
aws s3 cp "template-$(date +%Y%m%d%H%M%S).yaml" \
  s3://my-cfn-archive/templates/ --region us-east-1

# Execute the ChangeSet
aws cloudformation execute-change-set \
  --change-set-name "$CHANGESET_NAME" \
  --stack-name my-app-stack \
  --region us-east-1
```

---

## What the skill catches that a naive validation misses

| Configuration | Naive validation | Skill output | Why the skill is right |
|---|---|---|---|
| Validation depth | validate-template only | Four layers (cfn-lint + validate + cfn-nag + ChangeSet) | Each layer catches different issue classes |
| Security | Not checked | cfn-nag scans for wildcard IAM, unencrypted S3 | Security anti-patterns are invisible to validate-template |
| Change preview | No ChangeSet | ChangeSet with Action/Replacement per resource | Without ChangeSet, may accidentally replace stateful resources |
| Drift | Not checked | Drift detection before update | Out-of-band changes may be overwritten |
| Nested stacks | Parent only | Each child validated independently | Parent cfn-lint does NOT recurse into children |
| SAM | Linted directly | Expand first, then lint expanded template | cfn-lint has partial SAM support; expansion needed |
| Rollback | No archive | Template archived to S3 before update | Enables rollback if update fails |

---

## Related artifacts

- **Skill definition:** `skills/cloudformation-cfn-lint-operator/SKILL.md`
- **Linting and validation guide:** `skills/cloudformation-cfn-lint-operator/references/linting-and-validation.md`
- **Security and ChangeSet guide:** `skills/cloudformation-cfn-lint-operator/references/security-and-changesets.md`
- **Slash command:** `commands/aws/operate-cfn-lint.md`
- **Eval suite:** `skills/cloudformation-cfn-lint-operator/evals/evals.json`
- **Legacy test cases:** `skills/cloudformation-cfn-lint-operator/eval/test-cases.yaml`
