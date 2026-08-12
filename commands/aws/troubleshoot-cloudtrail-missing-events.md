---
allowed-tools: Read, Bash, Grep
description: "Diagnose CloudTrail missing events — trail disabled, bucket policy missing cloudtrail.amazonaws.com, org trail shadows member, data events opt-in, ReadWriteType filter, multi-region scope gap, KMS disabled, log file validation, CloudTrail Lake EDS, regional service gaps"
nl_triggers:
  - "CloudTrail missing events"
  - "CloudTrail events not appearing"
  - "CloudTrail trail not logging"
  - "CloudTrail IsLogging false"
  - "CloudTrail S3 bucket policy"
  - "CloudTrail data events missing"
  - "CloudTrail S3 data events"
  - "CloudTrail Lambda data events"
  - "CloudTrail management events"
  - "CloudTrail read-only events"
  - "CloudTrail event selector"
  - "CloudTrail multi-region trail"
  - "CloudTrail single-region"
  - "CloudTrail KMS key disabled"
  - "CloudTrail log encryption blocked"
  - "CloudTrail org trail not logging member"
  - "CloudTrail log file prefix"
  - "CloudTrail Lake empty"
  - "CloudTrail service not logging"
  - "troubleshoot CloudTrail missing events"
routes_to: cloudtrail-missing-events-troubleshooter
---

# /aws:troubleshoot-cloudtrail-missing-events

Activate the `cloudtrail-missing-events-troubleshooter` skill and
diagnose a CloudTrail missing-events incident.

## What it does

Reads the trail's failure signal (`describe-trails`,
`get-trail-status`, `get-event-selectors`, `get-bucket-policy`,
`describe-key`, `lookup-events`) and walks the symptom-to-cause
decision tree across eleven failure categories:

1. **TRAIL_DISABLED** — `get-trail-status` returns `IsLogging: false`.
2. **BUCKET_POLICY_BLOCKING** — `IsLogging: true` but
   `LatestDeliveryTime` stale; bucket policy missing
   `cloudtrail.amazonaws.com`.
3. **KMS_KEY_DISABLED** — `KmsKeyId` set and `KeyState: Disabled`.
4. **DATA_EVENTS_NOT_ENABLED** — data-plane API missing because
   event selector has no `DataResources`.
5. **EVENT_SELECTOR_READONLY** — `ReadWriteType: ReadOnly` or
   `WriteOnly` but operator expects the other.
6. **ORG_TRAIL_SHADOWS_MEMBER** — org trail shadows member trail.
7. **MULTI_REGION_SCOPE_GAP** — `IsMultiRegionTrail: false`.
8. **CW_LOGS_DELIVERY_DELAYED** — `lookup-events` shows events but
   CloudWatch Logs empty.
9. **LAKE_EDS_QUERY_ISSUE** — CloudTrail Lake query returns empty.
10. **SERVICE_NOT_IN_REGION** — service does not log in region.
11. **LOG_FILE_PREFIX_ERROR / LOG_FILE_VALIDATION_FAILED**.

## When to use

- A specific CloudTrail event is expected but `lookup-events` returns
  empty.
- The S3 bucket is not receiving CloudTrail log files.
- An org trail does not capture a specific member account's events.
- Data events (S3 GetObject, Lambda InvokeFunction) are absent
  despite the trail being `IsLogging: true`.
- `LatestDeliveryTime` is hours stale but `IsLogging: true`.

## Invocation

```
/aws:troubleshoot-cloudtrail-missing-events <description of the CloudTrail missing-events scenario>
```

## Output shape

```text
TARGET: <trail-name>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
ROOT_CAUSE: <one-sentence naming the failed configuration>
LAYER: <TRAIL_DISABLED | BUCKET_POLICY_BLOCKING | KMS_KEY_DISABLED |
        DATA_EVENTS_NOT_ENABLED | EVENT_SELECTOR_READONLY |
        ORG_TRAIL_SHADOWS_MEMBER | MULTI_REGION_SCOPE_GAP |
        CW_LOGS_DELIVERY_DELAYED | LAKE_EDS_QUERY_ISSUE |
        SERVICE_NOT_IN_REGION | LOG_FILE_PREFIX_ERROR | UNKNOWN>
EVIDENCE:
  - <symptom — the missing event or delivery gap>
  - <failing probe — command and its output>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <action with CLI command>
  2. <verification command>
CONFIRM: <state-changing operation approval gate>
```

## References

- Skill: `skills/cloudtrail-missing-events-troubleshooter/SKILL.md`
- Reference: `skills/cloudtrail-missing-events-troubleshooter/references/event-selectors-and-data-events-reference.md`
- Reference: `skills/cloudtrail-missing-events-troubleshooter/references/bucket-policy-and-org-trail-reference.md`
- AWS docs: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/
