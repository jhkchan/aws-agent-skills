# End-to-end usage scenario: inspector2-coverage-operator

A walkthrough showing the skill enabling delegated admin for an
AWS Organization, configuring org-wide coverage defaults, enabling
deep inspection on a member account's EC2 fleet, turning on ECR
rescan-on-push, and exporting an SBOM for audit.

## Input (user prompt)

> Configure Inspector v2 for our organization. Account 111111111111
> is the Organizations management account; designate 222222222222
> as delegated admin. From the delegated admin, enable EC2, ECR,
> and Lambda coverage for all new member accounts. Then enable
> EC2 deep inspection on member 333333333333's instances
> (i-0aaa, i-0bbb). Enable rescan-on-push on ECR repository
> prod-app in us-east-1. Finally, export an SBOM in CycloneDX 1.5
> format for the ECR images in account 111111111111.

## Skill output — enable-delegated-admin

```text
OPERATION: enable-delegated-admin
VERDICT: READY
TARGET: delegated-admin-account-id 222222222222
PRE_CHECKS:
  - [PASS] Caller 111111111111 is the Organizations management account
  - [PASS] list-delegated-admin-accounts returns no existing admin
  - [PASS] 222222222222 is a member of the org in root r-abc
STEPS:
  1. CONFIRM: About to enable-delegated-admin-account setting
     account 222222222222 as the delegated admin. This is one-way
     — member accounts can no longer self-disable. Proceed? (yes/no)
  2. aws inspector2 enable-delegated-admin-account \
       --delegated-admin-account-id 222222222222 \
       --client-token 1723305600
POST_VERIFY:
  - list-delegated-admin-accounts returns 222222222222 ENABLED
  - describe-organization-configuration succeeds from 222222222222
STATE: pending — delegated admin ACTIVE within ~30 seconds
NOTES:
  - Org-mode is one-way. Run update-organization-configuration
    separately to set autoEnable defaults.
```

## Skill output — update-organization-configuration

```text
OPERATION: update-org-config
VERDICT: READY
TARGET: autoEnable {ec2: true, ecr: true, lambda: true}
PRE_CHECKS:
  - [PASS] Caller 222222222222 is the delegated admin
  - [PASS] maxAccountLimitReached: false
  - [PASS] New autoEnable values do not disable existing members
STEPS:
  1. CONFIRM: About to update-organization-configuration setting
     autoEnable for EC2, ECR, Lambda. Applies to NEW members only.
     Proceed? (yes/no)
  2. aws inspector2 update-organization-configuration \
       --auto-enable '{ec2: true, ecr: true, lambda: true}' \
       --ec2-deep-inspection-configuration '{"enabled": true}' \
       --client-token 1723305601
POST_VERIFY:
  - describe-organization-configuration returns autoEnable all true
  - autoEnable applies only to NEW members; existing members retain
    state — audit each member separately
STATE: pending — org config ACTIVE within ~30 seconds
NOTES:
  - Existing members with EC2/ECR/Lambda DISABLED remain disabled.
  - Run enable --account-ids <list> to remediate existing members.
```

## Skill output — batch-update-ec2-deep-inspection-state

```text
OPERATION: update-ec2-deep-inspection
VERDICT: READY
TARGET: member 333333333333 instances i-0aaa, i-0bbb
PRE_CHECKS:
  - [PASS] Caller is delegated admin 222222222222
  - [PASS] 333333333333 relationshipStatus ENABLED
  - [PASS] SSM PingStatus Online for i-0aaa, i-0bbb
  - [PASS] SSM association AmazonInspector-ManageAWSAgent ACTIVE on
    i-0aaa, i-0bbb
STEPS:
  1. CONFIRM: About to set deep inspection state to ENABLED on
     i-0aaa, i-0bbb. First deep scan completes within 30-60 min.
     Proceed? (yes/no)
  2. aws inspector2 batch-update-ec2-deep-inspection-state \
       --instance-ids i-0aaa i-0bbb --scan-state ENABLED
POST_VERIFY:
  - batch-get-member-ec2-deep-inspection-state returns ACTIVE for
    i-0aaa, i-0bbb
  - First deep scan result visible in list-coverage within 30-60 min
STATE: pending — deep inspection ACTIVE within ~5 minutes
NOTES:
  - Deep inspection requires the AmazonInspector-ManageAWSAgent SSM
    association ACTIVE. Without it, deep scan silently no-ops.
```

## Skill output — configure-ecr-rescan

```text
OPERATION: configure-ecr-rescan
VERDICT: READY
TARGET: ECR repository prod-app in us-east-1
PRE_CHECKS:
  - [PASS] Repository prod-app exists
  - [PASS] Region us-east-1 supports ecr-enhanced
  - [PASS] Caller IAM role holds ecr:PutImageScanningConfiguration
STEPS:
  1. CONFIRM: About to put-image-scanning-configuration on prod-app
     setting scanOnPush=true. Every new image pushed will be scanned
     by Inspector automatically. Proceed? (yes/no)
  2. aws ecr put-image-scanning-configuration \
       --repository-name prod-app \
       --image-scanning-configuration scanOnPush=true \
       --region us-east-1
POST_VERIFY:
  - describe-image-scanning-configuration returns scanOnPush: true
  - Next push triggers a scan visible in describe-images
STATE: pending — scanOnPush ACTIVE immediately
NOTES:
  - Use scanOnPush: true for high-volume registries; concurrent
    manual start-image-scan calls are serialized per repository.
```

## Skill output — export-sbom (post-verification)

```text
OPERATION: export-sbom
VERDICT: COMPLETED
TARGET: reportId 0a1b2c3d-4e5f-6071-8290-abcd1234ef56
PRE_CHECKS:
  - [PASS] S3 bucket inspector-sbom-prod grants s3:PutObject to
    inspector2.amazonaws.com
  - [PASS] KMS key abcd1234 Enabled, grants kms:GenerateDataKey
  - [PASS] No concurrent SBOM export for this scope
STEPS:
  1. (executed) aws inspector2 start-sbom-export --report-format
     CYCLONEDX_1_5 --s3-destination ... --client-token 1723305602
POST_VERIFY:
  - [PASS] list-sbom-export returns status COMPLETED
  - [PASS] s3api head-object returns ContentLength 482310
STATE: COMPLETED — SBOM object at s3://inspector-sbom-prod/sbom/us-east-1/0a1b2c3d-...json
NOTES:
  - CycloneDX 1.5 format ready for ingestion into dependency-track
    or OWASP Dependency-Check.
```

## What the skill caught that a generic assistant misses

1. **Org-mode vs standalone:** A generic assistant runs `enable`
   from the member account, hitting `ConflictException`. The skill
   routes the operation to the delegated admin.
2. **autoEnable scope:** A generic assistant assumes
   `autoEnable: true` flips existing members. The skill surfaces
   that autoEnable applies ONLY to new members.
3. **SSM association for deep inspection:** A generic assistant
   calls `update-ec2-deep-inspection-configuration` without
   verifying the SSM association. Deep inspection silently no-ops.
4. **S3/KMS for SBOM:** A generic assistant runs `start-sbom-export`
   without verifying bucket and key policies. The export silently
   fails.
5. **CONFIRM gate:** A generic assistant auto-executes. The skill
   emits CONFIRM and waits — delegated admin enablement is one-way.
6. **Cost impact:** A generic assistant omits the per-scan-per-
   resource cost caveat. The skill surfaces it for broad
   enablements.
7. **Lambda runtime eligibility:** A generic assistant enables
   Lambda scanning without checking runtime support. The skill
   lists unsupported runtimes as gaps.

## Slash-command invocation

```
/aws:operate-inspector2-coverage
```

Or via the orchestrator:

```
/aws:pipeline
You: "enable Inspector v2 for all member accounts and turn on
      Lambda code scanning"
```

The orchestrator emits
`[Phase: Operate | Skills routed: inspector2-coverage-operator]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "enable inspector for all member accounts"
# [Phase: Operate | Skills routed: inspector2-coverage-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After enabling delegated admin and org-wide coverage:

```bash
# Verify delegated admin state
aws inspector2 list-delegated-admin-accounts --profile default \
  --query 'delegatedAdmins[0].{Id:accountId,Status:status}' \
  --output table

# Verify auto-enable defaults
aws inspector2 describe-organization-configuration --profile default \
  --query 'autoEnable' --output table

# Coverage gap audit per region
for region in us-east-1 us-west-2 eu-west-1; do
  echo "=== $region ==="
  aws inspector2 list-coverage --region $region --profile default \
    --filter-criteria 'SCAN_STATUS=_NOT_EQUALS=COMPLETED' \
    --output table
done
```
