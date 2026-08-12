# End-to-end usage scenario: s3-lifecycle-automator

A walkthrough showing the skill designing two lifecycle pipelines for
the same account: an AUTOMATION_DEPLOYED log archival policy with
versioning lifecycle, and a REVIEW_REQUIRED lifecycle with invalid
min-days that would silently fail. Demonstrates the min-days validation
gate and the versioning lifecycle design.

## Input (user prompt)

> Set up S3 lifecycle policies for our buckets. The log bucket needs
> archival tiers with version expiration. The data bucket needs the
> fastest possible transition to Glacier — we want IA at 15 days and
> Glacier at 45 days.

```
Design reference: prod-lifecycle-rollout
Account: 111111111111
Region: us-east-1

Bucket 1: app-access-logs
  Versioning: enabled
  Requirement: Standard -> IA (30d) -> Glacier IR (90d) -> Deep Archive (365d)
  Non-current version expiration: 120 days
  Abort incomplete multipart uploads: 7 days

Bucket 2: cost-optimization-target
  Versioning: disabled
  Requirement: Standard -> IA (15d) -> Glacier IR (45d)
  Operator says "we want the fastest possible transition."
```

## Skill output

```text
LIFECYCLE: prod-lifecycle-rollout
BUCKET: app-access-logs
POLICY:
  - Rule ID: log-archival-policy
  - Status: Enabled
  - Filter: Prefix "logs/"
TRANSITIONS:
  - Standard → Standard-IA: 30 days (min 30) — PASS
  - Standard-IA → Glacier IR: 90 days (min 90) — PASS
  - Glacier IR → Deep Archive: 365 days (min 180) — PASS
VERSIONING:
  - NoncurrentVersionTransition: 30 days → STANDARD_IA
  - NoncurrentVersionExpiration: 120 days
  - AbortIncompleteMultipartUpload: 7 days
  - ExpiredObjectDeleteMarker: true
VALIDATION:
  - Min-days check: PASS (all transitions meet enforced minimums)
  - Overlap check: PASS (single rule, non-overlapping prefix)
ENFORCEMENT:
  - Deployment: direct-CLI
  - Accounts: single (111111111111)
  - EventBridge: NOT WIRED (single-bucket, low-change-risk)
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws s3api put-bucket-lifecycle-configuration --bucket app-access-logs --lifecycle-configuration '{"Rules":[{"ID":"log-archival-policy","Status":"Enabled","Filter":{"Prefix":"logs/"},"Transitions":[{"Days":30,"StorageClass":"STANDARD_IA"},{"Days":90,"StorageClass":"GLACIER_IR"},{"Days":365,"StorageClass":"DEEP_ARCHIVE"}],"NoncurrentVersionTransitions":[{"NoncurrentDays":30,"StorageClass":"STANDARD_IA"}],"NoncurrentVersionExpiration":{"NoncurrentDays":120},"AbortIncompleteMultipartUpload":{"DaysAfterInitiation":7},"ExpiredObjectDeleteMarker":true}]}'

LIFECYCLE: prod-lifecycle-rollout (data bucket)
BUCKET: cost-optimization-target
POLICY:
  - Rule ID: fast-transition-policy
  - Status: Enabled
  - Filter: all objects
TRANSITIONS:
  - Standard → Standard-IA: 15 days (min 30) — FAIL
  - Standard-IA → Glacier IR: 45 days (min 90) — FAIL
VERSIONING:
  - NoncurrentVersionExpiration: NOT CONFIGURED
VALIDATION:
  - Min-days check: FAIL (2 violations)
ENFORCEMENT:
  - Deployment: NOT DEPLOYED (validation blocked)
VERDICT: REVIEW_REQUIRED
GAP: Two min-days violations detected. (1) Standard→Standard-IA at 15 days: enforced minimum is 30 days. The put-bucket-lifecycle-configuration API will silently accept this rule but it will NEVER execute — objects remain in Standard. Set Days to 30 or higher. (2) Standard-IA→Glacier IR at 45 days: enforced minimum is 90 days total object age. Set Days to 90 or higher. Alternatively, consider Intelligent-Tiering which has no transition-day minimums and auto-optimizes based on access patterns.
TEMPLATE: (corrected — set Days to 30 for IA and 90 for Glacier IR, then re-deploy. Or enable Intelligent-Tiering for immediate opt-in with auto-tiering.)
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for log archival;
REVIEW_REQUIRED for the fast-transition data bucket.**

## What the skill caught that a generic assistant misses

1. **The silent min-days failure.** A generic assistant deploys the
   15-day IA transition without validation. The API accepts it. The
   operator believes cost optimization is active. Objects never
   transition. The skill validates BEFORE deployment and blocks the
   rule.

2. **The versioning lifecycle gap.** A generic assistant deploys
   current-version transitions only. Non-current versions accumulate
   in Standard storage indefinitely. The skill includes
   NoncurrentVersionTransition, NoncurrentVersionExpiration, and
   AbortIncompleteMultipartUpload as a complete versioning policy.

3. **The GET-before-PUT rule.** A generic assistant calls
   `put-bucket-lifecycle-configuration` directly, replacing any
   existing policy. The skill backs up the current configuration
   first and merges.

4. **The Intelligent-Tiering alternative.** For the "fastest possible
   transition" requirement, a generic assistant tries to set
   impossibly low transition days. The skill recommends
   Intelligent-Tiering as the correct solution for aggressive
   tiering with no day constraints.

5. **The Storage Lens verification.** A generic assistant deploys and
   assumes it works. The skill includes a verification protocol using
   Storage Lens StorageClass distribution to confirm objects are
   actually transitioning over time.

## Slash-command invocation

```
/aws:automate-s3-lifecycle
```

Or via the orchestrator:

```
/aws:pipeline
You: "deploy S3 lifecycle policies for all buckets"
```

## CLI routing

```bash
node cli/bin/cli.js route "automate S3 lifecycle policy"
# [Phase: Automate | Skills routed: s3-lifecycle-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# List all buckets
aws s3api list-buckets \
  --query 'Buckets[].Name' --output table \
  --region us-east-1 --profile default

# Check existing lifecycle for a bucket
aws s3api get-bucket-lifecycle-configuration \
  --bucket app-access-logs \
  --region us-east-1 --profile default

# Check versioning status
aws s3api get-bucket-versioning \
  --bucket app-access-logs \
  --region us-east-1 --profile default

# Check Intelligent-Tiering configuration
aws s3api list-bucket-intelligent-tiering-configurations \
  --bucket data-lake-raw \
  --region us-east-1 --profile default

# Get Storage Lens configuration
aws s3control get-storage-lens-configuration \
  --config-id org-storage-lens \
  --account-id 111111111111 \
  --region us-east-1 --profile default

# Verify StackSet deployment status (multi-account)
aws cloudformation list-stack-instances \
  --stack-set-name s3-lifecycle-baseline \
  --query 'Summaries[].[Account,StackInstanceStatus.Status]' \
  --output table --region us-east-1 --profile default

# Verify objects are actually transitioning (post-deployment)
aws s3api head-object \
  --bucket app-access-logs \
  --key logs/2026-08-01/app.log \
  --query 'StorageClass' \
  --region us-east-1 --profile default
```

Then paste the output into the skill for lifecycle design.
