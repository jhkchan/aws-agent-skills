# Worked Examples

Blocks moved verbatim from SKILL.md in the agentskills.io progressive-disclosure
restructure. No content changed; load when a SKILL.md pointer stub applies.

## Worked example — PREREQUISITES_MISSING, no DLQ (moved from SKILL.md)

```text
PLAN: codebuild-notify-deploy
RULE:
  Name: codebuild-failed
  Bus: default
  Type: event-pattern
  Pattern: source=aws.codebuild, detail-type=CodeBuild Build State Change, detail.build-status=FAILED
  State: ENABLED
TARGETS:
  - notify-slack (Lambda): arn:aws:lambda:us-east-1:111111111111:function:notify-slack
    RetryPolicy: defaults (185 attempts / 24h) — too aggressive for notification
    DeadLetterConfig: NONE
    InputTransformer: no
    InvocationPermission: verified
RETRY: defaults (185 / 24h) — should be 3 / 900s
DLQ: NONE — silent event loss on Lambda failure
INPUT_TRANSFORM: full event
CROSS_ACCOUNT: none
PREREQUISITES:
  [x] Pattern validated via TestEventPattern
  [x] Target exists and ARN verified
  [ ] DLQ missing — create eventbridge-codebuild-failed-dlq
  [x] Lambda invocation permission verified
  [ ] CloudWatch alarm on DLQ depth not configured
  [ ] Idempotency note missing — CodeBuild emits multiple state-change events per build
VERDICT: PREREQUISITES_MISSING
GAP: (1) DLQ not configured — failed invocations will be silently dropped after retry exhaustion. (2) Default retry policy (185 attempts / 24h) is too aggressive for a Slack notification; should be 3 attempts / 900s. (3) No idempotency note — CodeBuild emits multiple state-change events per build (STARTED, IN_PROGRESS, FAILED, FAILED-retry); the Lambda will post duplicate Slack messages without dedup on detail.build-id + detail.build-status. (4) No CloudWatch alarm on DLQ depth. Address all four before deployment.
TEMPLATE: (incomplete — fix GAPs first)
```
