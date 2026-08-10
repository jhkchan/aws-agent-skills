---
allowed-tools: Read, Bash, Grep
description: "Diagnose CloudTrail logging gaps and missing events — data events vs management events, stopped trails, bucket-policy blocks, delivery delays, Insights disabled, and org trail member-account gaps"
nl_triggers:
  - "CloudTrail missing events"
  - "CloudTrail not logging"
  - "CloudTrail trail stopped"
  - "CloudTrail log delivery delayed"
  - "CloudTrail data events missing"
  - "CloudTrail Insights not working"
  - "CloudTrail org trail gap"
  - "CloudTrail member account not logged"
  - "CloudTrail S3 bucket policy"
  - "CloudTrail lookup-events returns empty"
  - "CloudTrail audit gap"
  - "CloudTrail silent"
  - "GetObject missing from CloudTrail"
  - "diagnose CloudTrail"
routes_to: cloudtrail-gap-troubleshooter
---

# /aws:troubleshoot-cloudtrail-gap

Activate the `cloudtrail-gap-troubleshooter` skill and diagnose a
CloudTrail logging gap.

## What it does

Reads the trail's failure signal (describe-trails, get-trail-status,
get-event-selectors, get-bucket-policy) and walks the symptom-to-cause
decision tree across seven categories:

1. MISSING_DATA_EVENTS — operator expects S3/Lambda/DynamoDB
   data-plane events; trail has no `DataResources` configured.
2. TRAIL_NOT_LOGGING — `get-trail-status` returns `isLogging: false`;
   trail was stopped or never started after IaC creation.
3. DELIVERY_DELAYED — `isLogging: true` but `latestDeliveryTime` lags
   beyond the 5-15 minute window (cross-region bucket, org aggregation).
4. INSIGHTS_DISABLED — operator expects an Insights finding;
   selectors missing, baseline not elapsed, or trail stopped.
5. ORG_TRAIL_GAP — org trail logs management account but a specific
   member account's events are missing (shadow trail stopped,
   delegated admin confusion, member left org).
6. MULTI_REGION_GAP — single-region trail; events from other regions
   not captured.
7. BUCKET_POLICY_BLOCKING — trail claims `isLogging: true` but no
   log files land in S3 (missing Allow, explicit Deny, KMS key
   policy, missing `bucket-owner-full-control` condition).

Emits a deterministic VERDICT per trail:

```text
INCIDENT: <account> / <trail-name> — <symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - describe-trails: <field>
  - get-trail-status: <field>
  - get-event-selectors: <field>
  - get-bucket-policy: <field>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific config change with field name>
  2. <verification command>
  3. <post-apply monitoring>
```

## When to invoke

Paste any of the following:

- A symptom ("GetObject events missing", "trail not logging", "Insights
  not firing", "member account not being logged").
- `aws cloudtrail describe-trails` / `get-trail-status` /
  `get-event-selectors` / `get-bucket-policy` output.
- A trail name + a gap description ("events from us-west-2 missing on
  corp-trail").

A bare trail name + any troubleshoot verb also routes here.

## Inputs

- Trail name (or "all trails" if unknown — the skill will list).
- `aws cloudtrail describe-trails --trail-name-list <name>` output.
- `aws cloudtrail get-trail-status --name <name>` output (critical —
  this is the canonical health signal).
- `aws cloudtrail get-event-selectors --trail-name <name>` for
  data-events-vs-management-events diagnosis.
- `aws s3api get-bucket-policy --bucket <bucket>` for bucket-policy
  blocking.
- For org trails: `aws organizations list-accounts` and the member
  account's `describe-trails --show-shadow-trails` output.

## Outputs

- One VERDICT block per trail/gap.
- EVIDENCE citing the specific API field and value.
- REMEDIATION with exact aws CLI commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for Governance / CloudTrail).
- `/aws:audit-cloudtrail-org-trail` for trail *posture* audits
  (encryption, validation, multi-region, retention) — separate from
  per-gap diagnosis.
- `/aws:troubleshoot-iam-permission` when the gap involves an IAM
  permission denial that may also surface in CloudTrail.
