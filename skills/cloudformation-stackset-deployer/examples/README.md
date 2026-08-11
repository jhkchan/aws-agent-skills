# End-to-End Example: CloudFormation StackSet Deployment

A walkthrough showing how to use the `cloudformation-stackset-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a baseline IAM roles template across all
accounts in a Security OU using a SERVICE_MANAGED StackSet. The
deployment needs:

- StackSet name: baseline-iam-roles
- Permission model: SERVICE_MANAGED
- Deployment target: OU ou-abc-12345678 (Security OU)
- Regions: us-east-1, us-west-2, eu-west-1
- Template: s3://my-bucket/templates/baseline-iam.yaml (18,432 bytes)
- Capabilities: CAPABILITY_IAM
- Managed execution: Active=true (continuous drift detection)
- Auto-deployment: Enabled, RetainStacksOnAccountRemoval=false
- Tags: Owner=platform, CostCenter=infra

Account: `111111111111`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-cloudformation-stackset
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a SERVICE_MANAGED StackSet named baseline-iam-roles
      targeting OU ou-abc-12345678 across us-east-1, us-west-2,
      eu-west-1. Template at s3://my-bucket/templates/baseline-iam.yaml.
      Enable managed execution. Account: 111111111111."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a cloudformation stackset"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
STACKSET: baseline-iam-roles (template: s3://my-bucket/templates/baseline-iam.yaml)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Permission model: SERVICE_MANAGED
  [✓] Organizations trusted access: Enabled
  [✓] Administration role: N/A (SERVICE_MANAGED SLR)
  [✓] Execution role: N/A (SERVICE_MANAGED SLR)
  [✓] Template source: s3://my-bucket/templates/baseline-iam.yaml (18,432 bytes)
  [✓] Capabilities: CAPABILITY_IAM
  [✓] Parameters: Environment=production, AuditRoleArn=arn:aws:iam::111111111111:role/audit
  [✓] Deployment targets: OrganizationalUnitIds=ou-abc-12345678
  [✓] Regions: us-east-1, us-west-2, eu-west-1 (RegionConcurrencyType=SEQUENTIAL)
  [✓] Operation preferences: FailureTolerancePercentage=5, MaxConcurrentPercentage=20
  [✓] Auto-deployment: Enabled=true, RetainStacksOnAccountRemoval=false
  [✓] Managed execution: Active=true (drift detection + auto-reconcile)
  [✓] Drift detection: managed-execution continuous
  [✓] Tags: Owner=platform, CostCenter=infra
VERIFICATION_COMMANDS:
  aws cloudformation describe-stack-set --stack-set-name baseline-iam-roles
  aws cloudformation list-stack-instances --stack-set-name baseline-iam-roles --output table
  aws organizations list-aws-service-access-for-organization --service-principal cloudformation.amazonaws.com
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the StackSet (registers it; does NOT deploy instances)
aws cloudformation create-stack-set \
  --stack-set-name baseline-iam-roles \
  --template-url https://s3.amazonaws.com/my-bucket/templates/baseline-iam.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=production \
    ParameterKey=AuditRoleArn,ParameterValue=arn:aws:iam::111111111111:role/audit \
  --capabilities CAPABILITY_IAM \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
  --managed-execution Active=true \
  --tags Key=Owner,Value=platform Key=CostCenter,Value=infra

# Step 2: Create stack instances (deploys to all accounts in the OU)
aws cloudformation create-stack-instances \
  --stack-set-name baseline-iam-roles \
  --deployment-targets OrganizationalUnitIds="ou-abc-12345678" \
  --regions "us-east-1,us-west-2,eu-west-1" \
  --operation-preferences \
    FailureTolerancePercentage=5,MaxConcurrentPercentage=20,\
    RegionConcurrencyType=SEQUENTIAL,RegionOrder=["us-east-1","us-west-2","eu-west-1"]

# Step 3: Wait for the operation to complete
aws cloudformation describe-stack-set-operation \
  --stack-set-name baseline-iam-roles \
  --operation-id <operation-id-from-step-2>
```

---

## Step 4 — Post-deployment verification

```bash
# StackSet status — Status: ACTIVE, DriftStatus: IN_SYNC
aws cloudformation describe-stack-set \
  --stack-set-name baseline-iam-roles \
  --query 'StackSet.[Status,PermissionModel,DriftStatus,ManagedExecution]'

# Stack instances — all should show SUCCEEDED
aws cloudformation list-stack-instances \
  --stack-set-name baseline-iam-roles \
  --output table

# Trusted access still enabled
aws organizations list-aws-service-access-for-organization \
  --service-principal cloudformation.amazonaws.com
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Permission model | Picks SELF_MANAGED by default | SERVICE_MANAGED for orgs | Immutable after creation; SERVICE_MANAGED auto-includes new accounts |
| Two-call sequence | Assumes create-stack-set deploys | Forces create-stack-instances | create-stack-set only registers; instances are separate |
| Management account | Expects it deployed | Flags it as skipped | SERVICE_MANAGED always skips management account |
| Operation preferences | Accepts defaults (0/1) | FailureTolerancePercentage=5, MaxConcurrentPercentage=20 | Defaults halt on first failure and deploy sequentially |
| Managed execution | Not mentioned | Active=true with drift + auto-reconcile | Enables continuous drift detection and targeting reconciliation |
| Capabilities | Often omitted | CAPABILITY_IAM explicitly cited | Omitting causes InsufficientCapabilities on every operation |

---

## Related artifacts

- **Skill definition:** `skills/cloudformation-stackset-deployer/SKILL.md`
- **Permission models and roles:** `skills/cloudformation-stackset-deployer/references/permission-models-and-roles.md`
- **Operation preferences and drift:** `skills/cloudformation-stackset-deployer/references/operation-preferences-and-drift.md`
- **Slash command:** `commands/aws/deploy-cloudformation-stackset.md`
- **Eval suite:** `skills/cloudformation-stackset-deployer/evals/evals.json`
- **Legacy test cases:** `skills/cloudformation-stackset-deployer/eval/test-cases.yaml`
