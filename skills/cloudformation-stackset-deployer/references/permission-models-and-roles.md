# Permission Models and IAM Roles — CloudFormation StackSet Deployer

Deep reference on the SELF_MANAGED vs SERVICE_MANAGED permission
models, the IAM role trust chains, Organizations trusted access,
and how to bootstrap the execution role across target accounts.
Loaded on demand by the skill — kept out of the main SKILL.md body
so the provisioning procedure stays scannable.

## Permission model comparison

| Dimension | SELF_MANAGED | SERVICE_MANAGED |
|---|---|---|
| Organizations required | No | Yes |
| Trusted access required | No | Yes |
| Role in admin account | AWSCloudFormationStackSetAdministrationRole | AWSServiceRoleForCloudFormationStackSetsOrgNS (SLR, auto-created) |
| Role in target accounts | AWSCloudFormationStackSetExecutionRole (must be pre-provisioned) | Service-linked role (auto-assumed via trusted access) |
| New accounts auto-deployed | No | Yes (if in a targeted OU) |
| Management account deployable | Yes | No (always skipped) |
| Switch model after creation | Must delete and recreate | Must delete and recreate |

## SELF_MANAGED: administration role

The administration role lives in the administrator account (the
account that calls `create-stack-set`).

**Trust policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudformation.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permission policy (minimum):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::*:role/AWSCloudFormationStackSetExecutionRole"
    }
  ]
}
```

The wildcard account ID in the Resource ARN allows the admin role
to assume the execution role in ANY target account. Tighten to
specific account ARNs for stricter blast radius control.

## SELF_MANAGED: execution role

The execution role lives in EVERY target account. CloudFormation
assumes this role (via the administration role) to create the
member stack.

**Trust policy (must reference the admin account ID):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<ADMIN_ACCOUNT_ID>:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permission policy (adjust to match the template's resources):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

The `iam:PassRole` permission is needed if the member stack passes
a service role (e.g., an IAM role for a Lambda function).

## SERVICE_MANAGED: trusted access one-time setup

Enable CloudFormation as a trusted service in Organizations:

```bash
aws organizations enable-aws-service-access \
  --service-principal cloudformation.amazonaws.com
```

Verify:

```bash
aws organizations list-aws-service-access-for-organization \
  --service-principal cloudformation.amazonaws.com
```

After enablement, CloudFormation creates the
`AWSServiceRoleForCloudFormationStackSetsOrgNS` service-linked role
in the management account. Member accounts receive a service-linked
role automatically when first targeted by a SERVICE_MANAGED
StackSet.

## Bootstrapping the execution role (SELF_MANAGED)

For SELF_MANAGED, the execution role must exist in every target
account BEFORE calling `create-stack-instances`. Common patterns:

### Pattern 1: Manual IAM in each account

Run in each target account (with that account's credentials):

```bash
aws cloudformation deploy \
  --template-file execution-role.yaml \
  --stack-name stackset-exec-role \
  --parameter-overrides AdminAccountId=<ADMIN_ACCOUNT_ID> \
  --capabilities CAPABILITY_IAM
```

Where `execution-role.yaml` creates the
`AWSCloudFormationStackSetExecutionRole`.

### Pattern 2: Cross-account assumption script

```bash
for ACCOUNT in 111111111111 222222222222 333333333333; do
  aws sts assume-role \
    --role-arn arn:aws:iam::$ACCOUNT:role/OpsBootstrap \
    --role-session-name bootstrap \
    --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' \
    --output text
  # Use returned credentials to deploy the execution role
done
```

### Pattern 3: AWS Control Tower / Landing Zone

If using Control Tower, include the execution role in the baseline
template so new accounts get it automatically at provisioning
time.

## Common role-related failures

| Symptom | Cause | Fix |
|---|---|---|
| `StackInstance` INOPERABLE | Execution role missing or misnamed in target account | Deploy `AWSCloudFormationStackSetExecutionRole` in target |
| `AccessDenied` on create-stack-instances | Admin role policy missing `sts:AssumeRole` on execution role ARN | Add `sts:AssumeRole` to admin role policy |
| `AccessDenied` for specific account only | Execution role trust policy missing that admin account ID | Add admin account ID to trust policy in target |
| `InvalidOperationException` (SERVICE_MANAGED) | Trusted access not enabled | `aws organizations enable-aws-service-access --service-principal cloudformation.amazonaws.com` |
| Service-linked role not created | Trusted access was disabled after StackSet creation | Re-enable trusted access; verify SLR exists |

## When to choose which model

**Choose SELF_MANAGED when:**
- Organizations is not enabled.
- You need to deploy to the management account itself.
- You have a non-Org account structure (e.g., merged acquisitions).
- You need per-account role customization.

**Choose SERVICE_MANAGED when:**
- Organizations is enabled.
- You want new accounts in OUs auto-deployed without manual
  intervention.
- You want to avoid per-account role bootstrapping.
- You want managed execution (continuous drift detection +
  auto-reconcile).

## References

- [Self-managed permissions](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-prereqs-self-managed.html)
- [Service-managed permissions](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-orgs-enable-trusted-access.html)
- [Booting StackSets execution role](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-prereqs-self-managed.html#stacksets-prereqs-accountsetup)

## SELF_MANAGED role handshake lifecycle (moved from SKILL.md)

The SELF_MANAGED permission model is the #1 source of "why won't my
stack instance deploy?" issues. A baseline model says "create the
roles and go"; this heuristic explains the actual trust chain.

```text
Administrator account:
  → AWSCloudFormationStackSetAdministrationRole
     trust: cloudformation.amazonaws.com
     policy: sts:AssumeRole on arn:aws:iam::<target>:role/AWSCloudFormationStackSetExecutionRole

For EACH target account:
  → AWSCloudFormationStackSetExecutionRole
     trust: arn:aws:iam::<admin-account-id>:root
     policy: cloudformation:* + iam:PassRole

On create-stack-instances:
  → CloudFormation assumes administration role → assumes execution role
    → creates member stack in target account

Common failures:
  → execution role missing/wrong name in target → INOPERABLE
  → trust policy missing admin account ID → AccessDenied
  → SCP blocking cloudformation → silent skip
```

**Key implication:** every target account must have the execution
role pre-provisioned (via a bootstrap StackSet or manual IAM).

## SERVICE_MANAGED trusted access setup (moved from SKILL.md)

SERVICE_MANAGED is simpler at scale but requires one-time
Organizations trusted-access enablement that a baseline model
often omits.

```text
One-time enablement (management account):
  aws organizations enable-aws-service-access \
    --service-principal cloudformation.amazonaws.com

Verify:
  aws organizations list-aws-service-access-for-organization \
    --service-principal cloudformation.amazonaws.com

Result:
  → CloudFormation creates AWSServiceRoleForCloudFormationStackSetsOrgNS
    SLR in the management account
  → Member accounts get a service-linked role when targeted
  → Trust path: CloudFormation → Organizations → member account SLR
  → No admin/execution role setup required
```

**Key implication:** if trusted access is later disabled, all
SERVICE_MANAGED StackSets become read-only until re-enabled. Treat
trusted access as a permanent dependency.
