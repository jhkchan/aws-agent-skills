# Step Functions Express Workflows Deployer - worked examples (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Output format - template block

```
EXPRESS_WORKFLOW: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Express-vs-Standard decision: EXPRESS (duration < 5 min, at-least-once acceptable)
  [✓|✗] Duration budget: p99 < 5 min (sync: p99 < 29s)
  [✓|✗] No .waitForTaskToken in ASL: verified
  [✓|✗] ASL definition validated: Distributed Map / .sync / AWS SDK as applicable
  [✓|✗] IAM execution role: least-privilege, service principal states.<region>.amazonaws.com
  [✓|✗] Logging: log-group /aws/states/<NAME>, level ALL|ERROR, includeExecutionData=true
  [✓|✗] Invocation mode: sync | async (sync caller timeout aligned)
  [✓|✗] EventBridge schedule + CloudWatch alarm: configured
  [✓|✗] Idempotency: side-effecting integrations have idempotency key
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands>
```

## Perfect example output - PREREQUISITES_MISSING

```text
EXPRESS_WORKFLOW: approval-flow
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Express-vs-Standard decision: EXPRESS requested
  [✗] Duration budget: workflow includes a 4-min Glue job plus a 2-min downstream ECS task; cannot fit in 5-min cap — migrate to STANDARD or split
  [✗] No .waitForTaskToken in ASL: FAILED — arn:aws:states:::sqs:sendMessage.waitForTaskToken at line 18; replace with .sync or STANDARD
  [✗] ASL definition validated: blocked pending integration fixes
  [✓] IAM execution role: scoped
  [✗] Logging: not yet attached — create /aws/states/approval-flow first
  [OPTIONAL] Invocation mode: not applicable pending ASL fix
  [OPTIONAL] EventBridge schedule: not requested
  [✗] Idempotency: cannot verify pending ASL fix
VERIFICATION_COMMANDS:
  grep -E ':waitForTaskToken' approval-flow.json
  aws logs create-log-group --log-group-name /aws/states/approval-flow
```

**Self-check before emit:**
- [ ] All 9 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] ASL contains NO `.waitForTaskToken` (verified by grep)?
- [ ] Logging row cites log group name + level (ALL or ERROR) + includeExecutionData?
- [ ] Sync caller timeout ≤ 29s verified (if sync mode)?
- [ ] Idempotency row cites the key source for each side-effecting integration?
- [ ] Express-vs-Standard row cites the cost-model comparison ($1/M vs $25/M)?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?

