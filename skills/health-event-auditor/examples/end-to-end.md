# End-to-end usage scenario: health-event-auditor

A walkthrough showing the skill auditing a real-world AWS Health
posture: an open EC2 degraded-performance event with two impaired
instances, paired with a missing EventBridge rule gap. Demonstrates
entity-status reasoning, multi-finding aggregation, and the
prescribed-action discipline.

## Input (user prompt)

> We just got paged about a Health event on the production EC2 fleet.
> Two instances are showing degraded performance. Audit the event and
> tell me what we're missing operationally.

```json
{
  "eventArn": "arn:aws:health:us-east-1::event/AWS_EC2_INSTANCE/AWS_EC2_INSTANCE_DEGRADED_PERFORMANCE/prod-fleet-incident",
  "eventTypeCategory": "issue",
  "eventStatus": "open",
  "service": "EC2",
  "eventTypeCode": "AWS_EC2_INSTANCE_DEGRADED_PERFORMANCE",
  "region": "us-east-1",
  "startTime": "2026-08-04T09:00:00Z",
  "lastUpdatedTime": "2026-08-05T03:30:00Z",
  "eventScopeCode": "ACCOUNT_SPECIFIC",
  "affectedEntities": [
    {"entityValue": "i-prod-app-1", "statusCode": "IMPAIRED", "region": "us-east-1"},
    {"entityValue": "i-prod-app-2", "statusCode": "IMPAIRED", "region": "us-east-1"}
  ]
}
```

Account posture:
- Support plan: Business
- AWS Region (API endpoint): us-east-1
- AWS Organization: present (8 member accounts)
- Health Organizational View: enabled
- EventBridge rules matching `aws.health`: NONE

## Skill output

```text
EVENT: arn:aws:health:us-east-1::event/AWS_EC2_INSTANCE/AWS_EC2_INSTANCE_DEGRADED_PERFORMANCE/prod-fleet-incident
VERDICT: UNRESOLVED_EVENT
REASON: Open issue event with both affected EC2 instances still IMPAIRED
(Step 1). Separately, no EventBridge rule matches `aws.health` on the
default bus — Health events are silently dropped (Step 3b).
FINDINGS:
  - [UNRESOLVED_EVENT] i-prod-app-1 and i-prod-app-2 are IMPAIRED for an
    open degraded-performance event — the operational impact is ongoing
    (Step 1)
  - [CONFIG_GAP] Zero EventBridge rules match source `aws.health` on the
    default bus — the production Health event that triggered this audit
    was not delivered to any automation (Step 3b)
  - [OK] Support tier is Business — Health API is callable (Step 0)
  - [OK] Health Organizational View is enabled — org-wide enumeration is
    possible (Step 3a)
REMEDIATION:
  1. UNRESOLVED_EVENT — Apply the prescribed action for
     AWS_EC2_INSTANCE_DEGRADED_PERFORMANCE: stop and start each impaired
     instance (NOT reboot — reboot does not migrate hosts):
       aws ec2 stop-instances --instance-ids i-prod-app-1 i-prod-app-2 \
         --region us-east-1
       # wait for both to reach Stopped
       aws ec2 start-instances --instance-ids i-prod-app-1 i-prod-app-2 \
         --region us-east-1
  2. UNRESOLVED_EVENT — Re-fetch entity status after 5-15 minutes:
       aws health describe-affected-entities \
         --filter eventArn=arn:aws:health:us-east-1::event/AWS_EC2_INSTANCE/AWS_EC2_INSTANCE_DEGRADED_PERFORMANCE/prod-fleet-incident \
         --region us-east-1 --output json
  3. CONFIG_GAP — Create the EventBridge rule:
       aws events put-rule --name HealthEventRouter \
         --event-bus-name default \
         --event-pattern '{"source":["aws.health"]}' \
         --region us-east-1
     Add a target (SNS topic that pages on-call):
       aws events put-targets --rule HealthEventRouter \
         --event-bus-name default \
         --targets file://health-targets.json --region us-east-1
```

## What the skill caught that a generic assistant misses

1. **Entity-level status is authoritative, not event-level.** A generic
   assistant sees "open event" and reports it. The skill explains that
   `IMPAIRED` entities mean the impact is ongoing — and that the event
   cannot be OK until every entity reports `RESOLVED`.

2. **Stop/start vs reboot.** Generic advice says "reboot the instance."
   The skill surfaces that reboot does NOT migrate hosts — only
   stop/start moves the instance to a new underlying host, which is the
   prescribed action for degraded-performance events.

3. **The CONFIG_GAP compounds the UNRESOLVED_EVENT.** Even though the
   verdict is UNRESOLVED_EVENT (worst finding), the missing EventBridge
   rule is a separate finding — the operator only learned about this
   event through a manual page, not automated delivery. Without the
   rule, the next event will also be silently dropped.

4. **API region is us-east-1, not the resource region.** The remediation
   commands target `--region us-east-1` for Health API calls and
   `--region us-east-1` for the EC2 calls (which happen to match here).
   The skill makes the region discipline explicit so the operator does
   not silently get empty results from a `--region us-west-2` Health
   call.

## Slash-command invocation

```
/aws:audit-health-event
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this Health event for the prod EC2 fleet"
```

The orchestrator emits
`[Phase: Audit | Skills routed: health-event-auditor]` and hands off
to this skill for the VERDICT.

## Live-account follow-up (requires AWS CLI)

After applying the prescribed actions and creating the EventBridge
rule, validate the posture:

```bash
# Verify entities transitioned to RESOLVED
aws health describe-affected-entities \
  --filter eventArn=arn:aws:health:us-east-1::event/AWS_EC2_INSTANCE/AWS_EC2_INSTANCE_DEGRADED_PERFORMANCE/prod-fleet-incident \
  --region us-east-1 --output json | jq '.entities[].statusCode'

# Confirm the EventBridge rule exists and has an active target
aws events list-rules --event-bus-name default --region us-east-1 | \
  jq '.Rules[] | select(.EventPattern | contains("aws.health"))'
aws events list-targets-by-rule --rule HealthEventRouter \
  --event-bus-name default --region us-east-1

# Confirm org-wide visibility for the next incident
aws health describe-health-service-status-for-organization \
  --region us-east-1
```

Then monitor CloudTrail for `events:PutEvents` from
`health.amazonaws.com` to confirm delivery resumes.
