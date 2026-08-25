# Control Tower Landing Zone — Reference

This reference details the Control Tower landing zone architecture,
guardrail taxonomy, Account Factory workflow, and drift detection
behaviors. Use alongside the SCP strategies reference.

## Landing Zone v2 architecture

Control Tower Landing Zone v2 (2024-2025) provisions:

- **Foundational accounts:** `audit` (Config aggregator + Security Hub
  delegated admin + GuardDuty delegated admin) and `log-archive`
  (CloudTrail organization trail S3 bucket + Config history bucket).
- **Organizational units:** `Security` (containing audit + log-archive),
  `Sandbox` (optional), plus custom OUs the operator creates.
- **Guardrails:** root-level preventive SCPs + detective Config rules.
- **Account Factory:** a Service Catalog product that vends new accounts
  with the baseline stack auto-deployed.
- **IAM Identity Center:** SSO across all member accounts with default
  permission sets.
- **CloudTrail organization trail:** delivering to the log-archive bucket.

## Guardrail taxonomy

### Preventive guardrails (SCPs)

| Guardrail | Type | Attach target | What it prevents |
|---|---|---|---|
| Disallow Root Access Keys | Strongly recommended | Root | Root account creating access keys |
| Disallow Member Account KMS Deletion | Strongly recommended | Root | Member deleting KMS keys |
| Disallow Member Account CloudTrail Changes | Strongly recommended | Root | Members disabling CloudTrail |
| Disallow Member Account VPC Changes | Strongly recommended | Root (optional at OU) | Members altering shared VPC |
| Enable AWS CloudTrail | Strongly recommended | Root | Disabling CloudTrail |
| Disallow Member Account IAM Role Creation | Elective | OU | Members creating IAM roles outside baseline |

Strongly recommended = attached at root; every account inherits.
Elective = attached at specific OU; only accounts in that OU inherit.

### Detective guardrails (Config rules)

| Guardrail | What it detects |
|---|---|
| Detect Public Read for S3 Buckets | S3 bucket with public-read policy |
| Detect Public Write for S3 Buckets | S3 bucket with public-write policy |
| Enable IAM Access Analyzer in Audit Account | Access Analyzer not enabled |
| Detect MFA Disabled on IAM Users | IAM user without MFA |
| Detect VPC Flow Logs Disabled | VPC without flow logs |

Detective guardrails run as Config rules; findings aggregate to Security
Hub via the aggregator in the audit account.

## Account Factory workflow

```bash
# Method 1: Control Tower native
aws controltower create-account \
  --account-name "workloads-prod-bu-a" \
  --account-email "aws+bu-a-prod@example.com" \
  --sso-user-email "bu-a-admin@example.com" \
  --sso-user-first-name "BUA" --sso-user-last-name "Admin"
```

The new account:
1. Inherits all root-level preventive guardrails.
2. Gets a baseline CloudFormation stack (CloudTrail enrollment, Config
   recorder, Security Hub enablement, default VPC hardening).
3. Is enrolled in IAM Identity Center with a default permission set.
4. Is auto-enrolled in the Config aggregator (org source).
5. Is auto-enrolled in GuardDuty + Security Hub (delegated admin).

Latency: 5-15 minutes from `create-account` to `AccountStatus=ACTIVE`.

### Method 2: Service Catalog (custom baseline, not on CT)

```bash
aws servicecatalog provision-product \
  --product-id <account-factory-product-id> \
  --provisioning-artifact-id <artifact-id> \
  --provisioned-product-name "bu-a-prod" \
  --provisioning-parameters \
    '[{"Key":"AccountName","Value":"workloads-prod-bu-a"},
      {"Key":"AccountEmail","Value":"aws+bu-a-prod@example.com"},
      {"Key":"SSOUserEmail","Value":"bu-a-admin@example.com"}]'
```

The Service Catalog product runs a CloudFormation template that calls
`organizations:create-account`, waits for ACTIVE, assumes the new
account's `OrganizationAccountAccessRole`, and deploys the baseline
stack via StackSets.

## Drift detection (Landing Zone v2)

Drift detection Lambda monitors CT-managed resources:

- **SCPs:** if a CT-managed preventive guardrail SCP is modified or
  detached, drift is detected and a Security Hub finding is raised.
- **Config rules:** if a CT-managed detective Config rule is modified
  or deleted, drift is detected.
- **Foundational accounts:** if the audit or log-archive account is
  modified (e.g., deleted CloudTrail trail), drift is detected.

**Important:** drift detection does NOT cover custom SCPs you attach.
A region-throttle SCP you add is invisible to drift detection — monitor
it with your own Config rule or Lambda.

Re-baseline after drift:

```bash
aws controltower update-landing-zone \
  --landing-zone-identifier <lz-identifier> \
  --manifest file://lz-manifest-v2.yaml
```

## Landing Zone upgrade (v1 to v2)

Pre-upgrade checklist:
1. Verify all accounts are in CT-managed OUs (not the root).
2. Verify no manual changes to CT-managed SCPs (drift will block upgrade).
3. Snapshot the current SCP tree (backup).
4. Schedule a maintenance window (upgrade takes 30-60 minutes, some
   guardrails may temporarily be in flux).

```bash
aws controltower update-landing-zone \
  --landing-zone-identifier <lz-id> \
  --manifest file://lz-v2-manifest.yaml \
  --tags Environment=prod ManagedBy=control-tower
```

Post-upgrade:
- Verify all accounts still enrolled in Config aggregator.
- Verify CloudTrail org trail still delivering.
- Verify Identity Center permission sets unchanged.
- Run a test Account Factory vending.

## Customizations for Landing Zone (2024-2025)

Native CT feature (replaces the legacy "Control Tower Customizations"
solution). Deploy custom resources alongside CT's baseline via Lambda +
CloudFormation templates.

```yaml
# lz-customization.yaml
Resources:
  CustomSCPRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument: ...
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AWSOrganizationsFullAccess
  CustomConfigRule:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: detect-public-ebs-snapshots
      Source:
        Owner: AWS
        SourceIdentifier: AWS:EBS_SNAPSHOT_PUBLIC_RESTORABLE_CHECK
```

Customizations apply to every new account vended via Account Factory.
Existing accounts are updated on the next LZ update.

## Region constraints

Control Tower historically required the management region be us-east-1.
Landing Zone v2 makes the management region configurable.

Supported management regions (as of 2025): us-east-1, us-west-2,
eu-west-1, eu-central-1, ap-southeast-1, ap-northeast-1. Verify the
current list in the Control Tower documentation before selecting.

The management region is set at LZ creation and cannot be changed post-
creation without a full LZ rebuild.

## Failure modes

- **Account Factory vending fails with `AccountStatus=CREATING` for >
  30 minutes.** Usually indicates the account email is invalid or the
  baseline CloudFormation stack failed. Check the audit account's
  CloudTrail for the failure event.

- **Drift detection not firing after manual SCP change.** Verify the
  drift detection Lambda is still deployed in the management region.
  Lambda can be accidentally deleted by a broad cleanup operation.

- **Account not enrolled in Config aggregator after creation.** Verify
  the aggregator is an OrganizationAggregationSource (not
  AccountAggregationSources). Org source auto-discovers; account source
  requires manual add per account.

- **Identity Center permission set not visible in new account.**
  Permission sets are region-specific. Verify the assignment was created
  in the same region as the Identity Center instance.

## Cost considerations

- Control Tower itself is free (no additional service charge).
- Underlying services bill normally: Config rules ($0.001/rule-evaluation),
  CloudTrail (free for first copy, S3 storage + Athena queries extra),
  Security Hub (per-check pricing), GuardDuty (per-GB-analyzed).
- For a 50-account org, budget $500-$2000/month in underlying service
  costs depending on workload volume.
## Landing Zone v2 (2024-2025) — creation command and capabilities

```bash
aws controltower create-landing-zone \
  --manifest file://lz-manifest.yaml \
  --tags Environment=prod ManagedBy=control-tower
```
v2 adds drift detection (Lambda monitors for manual SCP/Config changes;
raises a Security Hub finding), customizable guardrails, and lifecycle
controls on Account Factory.

## Create a new account via Account Factory (command and baseline inheritance)

```bash
aws controltower create-account \
  --account-name "workloads-prod-bu-a" \
  --account-email "aws+bu-a-prod@example.com" \
  --sso-user-email "bu-a-admin@example.com" \
  --sso-user-first-name "BUA" --sso-user-last-name "Admin"
```
The new account inherits all root-level guardrails and gets a baseline
stack (CloudTrail, Config, Security Hub, default VPC hardening) deployed
automatically.

## Account vending machine commands

```bash
aws organizations create-account \
  --email "aws+new-bu@example.com" \
  --account-name "bu-prod" \
  --iam-user-access-to-billing DENY \
  --role-name OrganizationAccountAccessRole
```

