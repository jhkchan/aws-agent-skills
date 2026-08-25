# EventBridge Rule Not Firing Troubleshooter — worked examples (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Input validation gate — INSUFFICIENT_DATA re-prompt (moved from SKILL.md)

If the input is malformed (missing RuleName, absent EventBusName, no
sample event for pattern diagnosis), emit:

```text
TARGET: <rule-name or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum the RuleName,
  the EventBusName, and a sample event payload to test against the
  pattern.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the RuleName and
  EventBusName, (2) a sample event that SHOULD have triggered the
  rule, and (3) for schedule-based rules, the ScheduleExpression
  string.
```

## Step 12: INSUFFICIENT_DATA output template (moved from SKILL.md)

```text
TARGET: <rule-name>
VERDICT: INSUFFICIENT_DATA
REASON: The available evidence does not conclusively identify a root
  cause. One or more probes returned ambiguous results or required
  operator input that was not provided.
LAYER: UNKNOWN
EVIDENCE:
  - <list what was probed and what was inconclusive>
REMEDIATION: Provide: (1) a sample event payload that should have
  triggered the rule, (2) the output of `describe-rule` including
  EventBusName and Targets, (3) for schedule-based rules, the exact
  ScheduleExpression string, and (4) for cross-account targets, the
  target Lambda's resource-based policy.
```

## Worked example — Schedule expression syntax (moved from SKILL.md)

```text
TARGET: ev-nightly-report-rule on default bus
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The rule's ScheduleExpression is "cron(0 9 * * *)" which has
  only 5 fields. EventBridge cron requires 6 fields (including Year).
  EventBridge auto-disabled the rule (State: DISABLED) due to the
  syntax error (Step 3a/3b).
LAYER: SCHEDULE_SYNTAX
EVIDENCE:
  - Symptom: schedule-based rule ev-nightly-report-rule never fires.
    describe-rule shows State: DISABLED.
  - Probe: aws events describe-rule returns ScheduleExpression:
    "cron(0 9 * * *)" and State: DISABLED.
  - Probe: The cron expression has 5 fields; EventBridge requires 6
    (Minutes Hours Day-of-month Month Day-of-week Year).
  - Passing: EventBusName is default (correct); the target Lambda has
    events.amazonaws.com principal; no EventPattern on the rule
    (schedule-based, not event-based).
REMEDIATION:
  1. Update the ScheduleExpression to use 6 fields:
     aws events put-rule --name ev-nightly-report-rule \
       --schedule-expression "cron(0 9 * * ? *)"
  2. Re-enable the rule (it was auto-disabled):
     aws events enable-rule --name ev-nightly-report-rule
  3. Verify:
     aws events describe-rule --name ev-nightly-report-rule \
       --output json | jq '{State, ScheduleExpression}'
     Expected: State: ENABLED, ScheduleExpression: "cron(0 9 * * ? *)"
CONFIRM: Before updating the rule, emit and await:
  "CONFIRM: About to update ev-nightly-report-rule schedule expression
   and re-enable. Proceed? (yes/no)"
```

## Worked example — Target Lambda missing EventBridge principal (moved from SKILL.md)

```text
TARGET: ev-order-processor-rule on custom.orders-bus
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The rule fires (test-event-pattern returns true, CloudTrail
  shows successful PutEvents), but the target Lambda fn-order-processor
  is never invoked. The Lambda's resource-based policy has no statement
  allowing events.amazonaws.com to invoke it. EventBridge's invocation
  is silently denied (Step 5b).
LAYER: TARGET_LAMBDA_PERMISSION
EVIDENCE:
  - Symptom: PutEvents returns 200; test-event-pattern returns Result:
    true; but the Lambda's CloudWatch logs show zero invocations.
  - Probe: aws lambda get-policy on fn-order-processor returns a policy
    with statements for API Gateway and S3, but NO statement for
    events.amazonaws.com.
  - Probe: aws cloudtrail lookup-events for the Lambda ARN in the last
    hour shows EventBridge invocation attempts returning AccessDenied.
  - Passing: EventBusName matches; rule State is ENABLED; pattern
    matches the event (test-event-pattern: true); rule has no RoleArn
    (same-account, service-linked role path).
REMEDIATION:
  1. Add the EventBridge principal to the Lambda resource-based policy:
     aws lambda add-permission \
       --function-name fn-order-processor \
       --statement-id EventBridgeInvoke \
       --action lambda:InvokeFunction \
       --principal events.amazonaws.com \
       --source-arn arn:aws:events:us-east-1:111111111111:rule/custom.orders-bus/ev-order-processor-rule
  2. Verify:
     aws lambda get-policy --function-name fn-order-processor \
       --output json | jq '.Policy | fromjson | .Statement[] |
         select(.Principal.Service == "events.amazonaws.com")'
     Expected: a statement with Action lambda:InvokeFunction and
     SourceArn matching the rule ARN.
CONFIRM: Before adding the permission, emit and await:
  "CONFIRM: About to add EventBridge invoke permission to
   fn-order-processor. Proceed? (yes/no)"
```
