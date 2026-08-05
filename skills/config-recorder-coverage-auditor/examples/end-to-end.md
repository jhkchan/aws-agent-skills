# End-to-end usage scenario: config-recorder-coverage-auditor

A walkthrough showing the skill auditing a multi-region AWS Config setup
that has a delivery channel failure (DELIVERY_GAP) in the primary region
and a missing global-resource-types flag (INCOMPLETE_COVERAGE) across the
account, demonstrating the layered classification and worst-verdict
aggregation.

## Input (user prompt)

> Audit our AWS Config setup across all enabled regions. We had an S3
> bucket cleanup last week and I'm worried something broke.

```
Audit reference: prod-config-audit-2026
Account: 111111111111
Regions: us-east-1, us-west-2, eu-west-1

=== us-east-1 ===
describe-configuration-recorders:
  name: default
  roleARN: arn:aws:iam::111111111111:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig
  recordingGroup:
    allSupported: true
    includeGlobalResourceTypes: true
    resourceTypes: []

describe-configuration-recorder-status:
  name: default
  recording: true
  lastStatus: SUCCESS

describe-delivery-channels:
  name: default
  s3BucketName: config-snapshots-prod-deleted
  configSnapshotDeliveryProperties:
    deliveryFrequency: Six_Hours

describe-delivery-channel-status:
  name: default
  lastStatus: FAILURE
  lastErrorCode: NO_SUCH_BUCKET
  lastErrorMessage: "The specified S3 bucket does not exist"

describe-config-rules:
  ConfigRules:
    - ConfigRuleName: s3-bucket-public-read-prohibited
      ConfigRuleState: ACTIVE
    - ConfigRuleName: iam-root-access-key-check
      ConfigRuleState: ACTIVE

describe-conformance-packs:
  ConformancePacks:
    - ConformancePackName: operational-best-practices
      DeploymentStatus: CREATE_COMPLETE

=== us-west-2 ===
describe-configuration-recorders:
  name: default
  recordingGroup:
    allSupported: true
    includeGlobalResourceTypes: false
    resourceTypes: []

describe-configuration-recorder-status:
  name: default
  recording: true
  lastStatus: SUCCESS

describe-delivery-channels:
  name: default
  s3BucketName: config-snapshots-prod
describe-delivery-channel-status:
  name: default
  lastStatus: SUCCESS

describe-config-rules:
  ConfigRules:
    - ConfigRuleName: ec2-volume-inuse-check
      ConfigRuleState: ACTIVE

describe-conformance-packs: (empty)

=== eu-west-1 ===
describe-configuration-recorders:
  name: default
  recordingGroup:
    allSupported: true
    includeGlobalResourceTypes: false
    resourceTypes: []

describe-configuration-recorder-status:
  name: default
  recording: true
  lastStatus: SUCCESS

describe-delivery-channels:
  name: default
  s3BucketName: config-snapshots-prod
describe-delivery-channel-status:
  name: default
  lastStatus: SUCCESS

describe-config-rules: (empty)
describe-conformance-packs: (empty)
```

## Skill output

```text
AUDIT: prod-config-audit-2026
REGION: us-east-1
VERDICT: DELIVERY_GAP
REASON: Recorder is running with allSupported and includeGlobalResourceTypes
enabled (Step 1 OK), but delivery channel status is FAILURE with
lastErrorCode NO_SUCH_BUCKET — the S3 bucket was deleted, snapshots are not
being delivered (Step 2).
FINDINGS:
  - [OK] Recorder exists, recording: true, lastStatus: SUCCESS, allSupported:
    true, includeGlobalResourceTypes: true (Step 1)
  - [DELIVERY_GAP] Delivery channel lastStatus: FAILURE, lastErrorCode:
    NO_SUCH_BUCKET — bucket "config-snapshots-prod-deleted" does not exist
    (Step 2)
  - [OK] Config rules deployed: s3-bucket-public-read-prohibited,
    iam-root-access-key-check (Step 4)
REMEDIATION:
  1. Recreate the S3 bucket or update the delivery channel:
     aws configservice put-delivery-channel \
       --delivery-channel name=default,s3BucketName=config-snapshots-prod \
       --region us-east-1
  2. Verify delivery resumes:
     aws configservice describe-delivery-channel-status --region us-east-1

AUDIT: prod-config-audit-2026
REGION: us-west-2
VERDICT: NO_RULES_PARTIAL
...
```

**Account-level aggregate verdict: DELIVERY_GAP** (worst across all
regions — us-east-1's broken delivery channel is the priority fix).

## What the skill caught that a generic assistant misses

1. **The two-API-call recorder check.** A generic assistant checks
   `describe-configuration-recorders` and sees a healthy-looking config.
   The skill requires BOTH the configuration AND the status API — the
   config looks fine but the delivery status reveals the FAILURE.

2. **The `lastErrorCode` diagnostic.** A generic assistant says "delivery
   is failing." The skill surfaces `NO_SUCH_BUCKET` and explains the S3
   bucket was deleted during the cleanup, giving the operator the exact
   remediation path (recreate bucket or update channel).

3. **The multi-region global-resource-types analysis.** Only us-east-1
   has `includeGlobalResourceTypes: true`. The skill confirms this is the
   correct single-region pattern and does NOT flag the other regions for
   having it disabled — avoiding false positives.

4. **eu-west-1 has zero rules.** The skill flags this as a NO_RULES
   finding but the overall verdict is DELIVERY_GAP (worse). The layered
   FINDINGS let the operator see both issues at once.

## Slash-command invocation

```
/aws:audit-config-recorder-coverage
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit Config coverage across all regions"
```

## CLI routing

```bash
node cli/bin/cli.js route "audit AWS Config coverage"
# [Phase: Audit | Skills routed: config-recorder-coverage-auditor]
```

## Live-account invocation (requires AWS CLI)

```bash
# Single-region audit
for api in describe-configuration-recorders \
           describe-configuration-recorder-status \
           describe-delivery-channels \
           describe-delivery-channel-status \
           describe-config-rules \
           describe-conformance-packs; do
  echo "=== $api ==="
  aws configservice $api --region us-east-1 --profile default --output json
done

# Multi-region sweep
for region in $(aws ec2 describe-regions \
  --filters OptInStatus=opt-in-status \
  --query 'Regions[].RegionName' --output text --profile default); do
  echo "######## $region ########"
  aws configservice describe-configuration-recorders --region $region --profile default
  aws configservice describe-configuration-recorder-status --region $region --profile default
  aws configservice describe-delivery-channel-status --region $region --profile default
  aws configservice describe-config-rules --region $region --profile default --query 'length(ConfigRules)'
  aws configservice describe-conformance-packs --region $region --profile default --query 'length(ConformancePacks)'
done
```

Then paste the output into the skill for classification.
