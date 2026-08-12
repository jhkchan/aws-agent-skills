# End-to-end usage scenario: backup-vault-compliance-automator

A walkthrough showing the skill designing a complete backup vault
compliance rollout: vault policy enforcement, compliance-mode Vault
Lock deployment, coverage audit with Config rules, and cross-region
replication verification across an Organizations fleet.

## Input (user prompt)

> Deploy backup vault compliance across our production environment.
> We need SEC 17a-4 compliance (immutable 7-year retention), vault
> policies denying unencrypted backups, Config rules for continuous
> monitoring, and cross-region replication to us-west-2. We have 85
> resources, 3 of which lack backup tags.

```
Design reference: prod-backup-compliance-rollout
Account: 111111111111 (management account)
Region: us-east-1

Vaults:
  prod-backup-vault (us-east-1) — 50 recovery points, no lock
  prod-backup-vault-dr (us-west-2) — empty, for cross-region copies

Requirement:
  - Vault Lock: COMPLIANCE mode, MinRetention=2557d (7 years)
  - Vault policy: deny non-encrypted, enforce approved KMS key
  - KMS key: arn:aws:kms:us-east-1:111111111111:key/prod-backup-key
  - Cross-region: copy to us-west-2 with separate KMS key

Resources: 85 total (EC2=40, RDS=15, DynamoDB=20, EFS=10)
  Covered: 82 (tag-based BackupPlan=prod selection)
  Gap: 3 EC2 instances without BackupPlan tag

Config rules: none currently deployed
Delegated admin: not yet configured
Organization: 30 member accounts
```

## Skill output

```text
COMPLIANCE: prod-backup-compliance-rollout
VAULT: prod-backup-vault (account-wide) + prod-backup-vault-dr (cross-region)
POLICY:
  - Vault policy: deny-non-encrypted, enforce-approved-kms, enforce-tls
  - KMS enforcement: arn:aws:kms:us-east-1:111111111111:key/prod-backup-key
  - Cross-account: source accounts in OU r-xxxx allowed via PrincipalAccount condition
LOCK:
  - Mode: COMPLIANCE
  - MinRetention: 2557 days (7 years — SEC 17a-4)
  - MaxRetention: 2557 days
  - CoolOff: 3 days (ChangeableForDays=3)
  - Validation: governance mode tested in staging, all parameters verified
COVERAGE:
  - Total resources: 85 (EC2=40, RDS=15, DynamoDB=20, EFS=10)
  - Covered: 82 (by tag BackupPlan=prod)
  - Gap: 3 EC2 instances without BackupPlan tag
  - Config rule: ec2-must-have-backup-plan (custom Lambda) deployed
  - Remediation: manual tag application recommended, auto-tag SSM doc wired
REPLICATION:
  - Cross-region: us-west-2, COMPLETED (last 10 copy jobs verified)
  - Destination vault: prod-backup-vault-dr (us-west-2)
  - Destination KMS: arn:aws:kms:us-west-2:111111111111:key/dr-backup-key
VERDICT: AUTOMATION_DEPLOYED
GAP: 3 untagged EC2 instances must be tagged before they are production-critical
COVERAGE_GAP: 3
UNENCRYPTED_RECOVERY_POINTS: 0
TEMPLATE:
  # 1. Vault policy
  aws backup put-backup-vault-policy --backup-vault-name prod-backup-vault --policy file://vault-policy.json
  # 2. Vault Lock (compliance mode, 7-year retention)
  aws backup put-backup-vault-lock-configuration --backup-vault-name prod-backup-vault --changeable-for-days 3 --min-retention-days 2557 --max-retention-days 2557 --mode COMPLIANCE
  # 3. Config rules
  aws configservice put-config-rule --config-rule '{"ConfigRuleName":"backup-recovery-point-encrypted","Source":{"Owner":"AWS","SourceIdentifier":"backup-recovery-point-encrypted"}}'
  # 4. Custom coverage rule
  aws configservice put-config-rule --config-rule '{"ConfigRuleName":"ec2-must-have-backup-plan","Source":{"Owner":"CUSTOM_LAMBDA","SourceIdentifier":"arn:aws:lambda:us-east-1:111111111111:function:check-ec2-backup-coverage"},"Scope":{"ComplianceResourceTypes":["AWS::EC2::Instance"]}}'
  # 5. Aggregator
  aws configservice put-configuration-aggregator --configuration-aggregator-name org-backup-compliance --organization-aggregator-source '{"RoleArn":"arn:aws:iam::111111111111:role/ConfigAggregatorRole","AllAwsRegions":true}'
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED.** The vault
policy enforces encryption. The Vault Lock in compliance mode
provides SEC 17a-4 immutability. Config rules detect coverage gaps
and encryption non-compliance continuously. Cross-region replication
is verified.

## What the skill caught that a generic assistant misses

1. **The compliance vs governance mode distinction.** A generic
   assistant may deploy governance mode without understanding it
   does not meet SEC 17a-4. The skill mandates compliance mode for
   regulatory immutability and flags governance as insufficient.

2. **The cool-off period management.** A generic assistant sets the
   lock and moves on. The skill documents the 3-day cool-off window,
   verifies parameters are correct before it expires, and confirms
   the lock is permanent afterward.

3. **The coverage gap detection.** A generic assistant does not
   check whether all resources have backup plans. The skill identifies
   the 3 untagged EC2 instances, deploys a Config rule for continuous
   detection, and recommends tagging remediation.

4. **The MaxRetention parameter.** A generic assistant omits
   MaxRetention. The skill sets it to match the regulatory maximum
   (2557 days) to prevent excessively long retention that inflates
   storage costs.

5. **The destination-region KMS key.** A generic assistant may use
   the source-region KMS key ARN for cross-region copy. The skill
   identifies that KMS keys are region-specific and configures a
   separate destination-region key.

6. **The Config aggregator.** A generic assistant deploys Config
   rules in one account. The skill sets up an organization-level
   aggregator so compliance status is visible across all 30 member
   accounts from the management account.

7. **The Vault Lock pre-validation protocol.** A generic assistant
   deploys compliance mode directly. The skill requires testing in
   governance mode first to verify all parameters before the
   irreversible compliance-mode deployment.

## Slash-command invocation

```
/aws:automate-backup-compliance
```

Or via the orchestrator:

```
/aws:pipeline
You: "enforce backup vault compliance"
```

## CLI routing

```bash
node cli/bin/cli.js route "backup vault compliance"
# [Phase: Automate | Skills routed: backup-vault-compliance-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# Discover all backup vaults and their lock state
aws backup list-backup-vaults \
  --output table \
  --query 'BackupVaultList[*].[BackupVaultName,LockState,NumberOfRecoveryPoints]' \
  --region us-east-1 --profile default

# Check vault policy
aws backup get-backup-vault-policy \
  --backup-vault-name prod-backup-vault \
  --region us-east-1 --profile default

# Check recovery point encryption
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name prod-backup-vault \
  --output json \
  --query 'RecoveryPoints[*].[RecoveryPointArn,Status,EncryptionKeyArn]' \
  --region us-east-1 --profile default

# List backup plans and selections
aws backup list-backup-plans \
  --output json \
  --query 'BackupPlansList[*].[BackupPlanId,BackupPlanName]' \
  --region us-east-1 --profile default

# Check cross-region copy jobs
aws backup list-copy-jobs \
  --by-state COMPLETED \
  --output json \
  --region us-east-1 --profile default

# Verify destination region recovery points
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name prod-backup-vault-dr \
  --output json \
  --region us-west-2 --profile default

# Check existing Config rules
aws configservice describe-config-rules \
  --config-rule-names backup-recovery-point-encrypted \
  --region us-east-1 --profile default
```

Then paste the output into the skill for compliance workflow design.
