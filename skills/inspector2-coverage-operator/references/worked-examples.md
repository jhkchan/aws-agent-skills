# Worked examples and CLI patterns — inspector2-coverage-operator

Secondary worked examples and CLI boilerplate patterns, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## CLI boilerplate patterns (moved from SKILL.md)

### Enable Inspector for EC2 + ECR + Lambda (standalone account)

```bash
aws inspector2 enable \
  --account-ids 111111111111 \
  --client-token "$(date +%s)" \
  --resource-types EC2 ECR LAMBDA \
  --region us-east-1
```

Lambda code vulnerability scanning is enabled alongside LAMBDA;
no separate flag needed.

### Configure delegated admin for Organizations-wide coverage

```bash
# From the Organizations MANAGEMENT account
aws inspector2 enable-delegated-admin-account \
  --delegated-admin-account-id 222222222222 \
  --client-token "$(date +%s)"

# From the DELEGATED ADMIN account, set auto-enable defaults
aws inspector2 update-organization-configuration \
  --auto-enable '{ec2: true, ecr: true, lambda: true}' \
  --client-token "$(date +%s)"
```

`autoEnable` applies ONLY to NEW member accounts. Existing members
keep their pre-config state.

### Associate a member account (from delegated admin)

```bash
aws inspector2 associate-member \
  --account-id 333333333333 \
  --client-token "$(date +%s)"
```

The member must already be in the org. After association,
`list-members` returns `relationshipStatus: ENABLED`.

### Enable EC2 deep inspection (org-level default)

```bash
# From the delegated admin
aws inspector2 update-organization-configuration \
  --auto-enable '{ec2: true, ecr: true, lambda: true}' \
  --ec2-deep-inspection-configuration '{
    "enabled": true,
    "packageNameFilters": ["kernel", "openssl"]
  }'
```

Instances opt in/out via `batch-update-ec2-deep-inspection-state
--instance-ids i-aaa i-bbb --scan-state ENABLED`. The SSM
association `AmazonInspector-ManageAWSAgent` must be `ACTIVE`.

### Enable ECR rescan-on-push for a repository

```bash
aws ecr put-image-scanning-configuration \
  --repository-name prod-app \
  --image-scanning-configuration scanOnPush=true \
  --region us-east-1
```

Inspector uses this setting. Without `scanOnPush: true`, Inspector
scans only on `start-image-scan`. Enhanced scans (`ecr-enhanced`)
pull the Inspector agent for deep package inventory.

### Verify Lambda code vulnerability scanning is active

```bash
aws inspector2 list-coverage \
  --filter-criteria 'RESOURCE_TYPE=_EQUALS=LAMBDA_FUNCTION' \
  --region us-east-1 \
  --output table
```

Coverage rows with `scanType: LAMBDA_CODE` are scanned. Functions
in unsupported runtimes (`dotnet6`, `ruby`) are absent — surface as
a gap.

### Start SBOM export (CycloneDX format)

```bash
aws inspector2 start-sbom-export \
  --report-format CYCLONEDX_1_5 \
  --s3-destination '{
    "bucketName": "inspector-sbom-prod",
    "kmsKeyArn": "arn:aws:kms:us-east-1:111111111111:key/abcd1234",
    "keyPrefix": "sbom/us-east-1/"
  }' \
  --resource-filter-criteria '{
    "accountId": [{"comparison": "EQUALS", "value": "111111111111"}],
    "resourceType": [{"comparison": "EQUALS", "value": "AWS_ECR_CONTAINER_IMAGE"}]
  }' \
  --client-token "$(date +%s)"
```

Returns a `reportId`. Poll via `list-sbom-export --report-id <id>`
until `status: COMPLETED`. The S3 object appears at
`s3://<bucket>/<keyPrefix><reportId>.json`.

## Worked example — enable delegated admin (READY) (moved from SKILL.md)

```text
OPERATION: enable-delegated-admin
VERDICT: READY
TARGET: delegated-admin-account-id 222222222222
PRE_CHECKS:
  - [PASS] Caller is the Organizations management account 111111111111
  - [PASS] list-delegated-admin-accounts returns no existing
    delegated admin for Inspector
  - [PASS] Target account 222222222222 is a member of the org in
    the same root
STEPS:
  1. CONFIRM: About to enable-delegated-admin-account setting
     account 222222222222 as the delegated admin. Only the
     delegated admin can manage member enable/disable afterwards.
     Proceed? (yes/no)
  2. aws inspector2 enable-delegated-admin-account \
       --delegated-admin-account-id 222222222222 \
       --client-token 1723305600
POST_VERIFY:
  - list-delegated-admin-accounts returns 222222222222 with
    status: ENABLED
  - describe-organization-configuration succeeds from the delegated
    admin account
STATE: pending — delegated admin ACTIVE within ~30 seconds
NOTES:
  - Org-mode is one-way: member accounts cannot self-disable.
  - Run update-organization-configuration separately to set
    autoEnable defaults for new member accounts.
```

## Worked example — diagnose EC2 coverage gap (BLOCKED) (moved from SKILL.md)

```text
OPERATION: diagnose-coverage
VERDICT: BLOCKED
TARGET: account 111111111111 region us-east-1 EC2
PRE_CHECKS:
  - [PASS] batch-get-account-status returns state: ENABLED for EC2
    in us-east-1
  - [FAIL] 3 of 12 instances report AGENT_OFFLINE in list-coverage
    (i-aaa, i-bbb, i-ccc). SSM PingStatus ConnectionLost. Inspector
    requires the SSM agent online; deep inspection requires
    AmazonInspector-ManageAWSAgent ACTIVE.
  - [PASS] 9 of 12 instances report COMPLETED scan in last 24h
STEPS: (none — pre-checks failed; this is a diagnosis)
POST_VERIFY: (none)
STATE: FAILED — 3 instances offline for Inspector scanning
NOTES:
  - Remediation: install/restart the SSM agent on i-aaa, i-bbb,
    i-ccc. Verify the instance profile includes
    AmazonSSMManagedInstanceCore. Re-scan is automatic once
    PingStatus returns Online.
  - For deep inspection, verify the
    AmazonInspector-ManageAWSAgent SSM association is Associated:
    true on each instance.
```
