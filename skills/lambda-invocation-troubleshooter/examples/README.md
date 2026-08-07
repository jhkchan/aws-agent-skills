# Example usage: lambda-invocation-troubleshooter

A walkthrough showing the skill diagnosing a TaskTimeoutException that
mimics a downstream-service outage, demonstrating the symptom-to-layer
triage, the memory-vs-timeout decision (CPU scales with memory), the
evidence-backed ROOT_CAUSE_FOUND verdict, and the downstream-service
root cause.

## Input (user prompt)

> Our payments webhook Lambda started failing at 03:17 UTC. About 30%
> of invocations return TaskTimeoutException after exactly 30 seconds.
> We've been debugging this as a Lambda timeout issue for 30 minutes —
> please help us find the actual root cause.

```text
FunctionName: fn-payments-webhook
Qualifier: prod (version 42)
Runtime: nodejs20.x
Timeout: 30
MemorySize: 512
Handler: index.handler
PackageType: Zip
VpcConfig: (none — function is not VPC-attached)
LastUpdateStatus: Successful (last update 2 days ago)
Execution role: arn:aws:iam::111111111111:role/fn-payments-webhook-role

Recent log pattern:
  INFO  Putting item to orders-table (id=...)
  (no further log line)
  END RequestId: ... Duration: 30000.00 ms Billed Duration: 30000 ms
    Memory Size: 512 MB Max Memory Used: 78 MB
  Task timed out after 30.00 seconds

70% of invocations complete in 1-3s with "Put complete".

CloudWatch metrics (last hour):
  - Duration p50: 1.2s, p99: 30s, Maximum: 30s
  - Errors: 47 (matches the TaskTimeoutException count)
  - MemoryUtilization Maximum: 15% (memory is not the issue)
```

## Skill output

```text
TARGET: fn-payments-webhook (alias: prod, version 42)
VERDICT: ROOT_CAUSE_FOUND
REASON: Function Timeout is 30s; CloudWatch Duration Maximum is exactly
  30000 ms on 47 invocations in the last hour (function is killed at
  the cap). The last log line before each kill is "Putting item to
  orders-table" — the DynamoDB PutItem is the slow operation. The
  table's WriteCapacityUnits is 100 on a provisioned-mode table
  sustaining 5000+ WCU of demand; CloudWatch shows sustained
  WriteThrottleEvents in the same window. Memory is not the issue
  (Max Memory Used 78 MB out of 512 MB allocated) (Step 2b/2c).
LAYER: TIMEOUT_DOWNSTREAM
EVIDENCE:
  - Symptom: 30% of invocations return TaskTimeoutException after
    exactly 30.00 seconds; 70% succeed in 1-3s. The timeout pattern
    is bursty (correlates with traffic peaks), not consistent (which
    would suggest a config-only timeout issue).
  - Probe: aws logs filter-log-events returns "Task timed out after
    30.00 seconds" 47 times in the last hour; the preceding log line
    in every case is "Putting item to orders-table".
  - Probe: aws cloudwatch get-metric-statistics on aws/dynamodb
    WriteThrottleEvents for orders-table returns sustained throttling
    in the same hour.
  - Probe: aws dynamodb describe-table returns BillingModeSummary
    PAY_PER_REQUEST not set (table is PROVISIONED);
    ProvisionedThroughput.WriteCapacityUnits = 100.
  - Passing: aws cloudwatch MemoryUtilization Maximum = 15% (memory
    is not the issue); function is not VPC-attached (network is not
    the issue); function role has dynamodb:PutItem on orders-table
    (permissions verified via simulate-principal-policy).
REMEDIATION:
  1. Switch the table to on-demand billing to absorb the burst:
     aws dynamodb update-table --table-name orders-table \
       --billing-mode PAY_PER_REQUEST --profile <p>
  2. Optionally raise the Lambda Timeout to 60s as defence-in-depth
     against transient spikes:
     aws lambda update-function-configuration --function-name \
       fn-payments-webhook --timeout 60 --profile <p>
  3. Publish a new version and shift the prod alias AFTER the table
     billing-mode change completes:
     aws lambda publish-version --function-name fn-payments-webhook
     aws lambda update-alias --name prod --function-version <new>
  4. Verify by re-invoking and watching CloudWatch Duration over the
     next 30 minutes; Duration Maximum should drop below 5s.
CONFIRM: Before updating the table or function, emit and await:
  "CONFIRM: About to switch orders-table to PAY_PER_REQUEST and raise
   fn-payments-webhook Timeout to 60s. Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Distinguished config timeout from downstream timeout.** A generic
   assistant says "raise the timeout." The skill recognises that the
   timeout pattern is bursty (30% of invocations at the cap, 70%
   succeeding in 1-3s) — that pattern indicates a downstream issue
   under load, not a config timeout that would affect every invocation
   uniformly.

2. **Identified the slow operation via the last log line.** The skill
   reads the log stream immediately before each `Task timed out` entry
   and identifies "Putting item to orders-table" as the operation in
   flight. The downstream target (DynamoDB) is the next probe, not the
   function code.

3. **Ruled out memory via the Max Memory Used metric.** A common
   misdiagnosis on Lambda timeouts is "raise memory" — which DOES help
   for CPU-bound timeouts but NOT for downstream-latency timeouts. The
   skill's `MemoryUtilization Maximum: 15%` evidence rules out the
   memory/timeout misdiagnosis with positive evidence.

4. **Found the throttling on the downstream.** The skill cross-
   references CloudWatch `WriteThrottleEvents` on the DynamoDB table
   and confirms `BillingModeSummary: PROVISIONED` with
   `WriteCapacityUnits: 100`. The root cause is DynamoDB capacity, not
   Lambda config.

5. **Recommended the table-side fix, not the function-side fix.** The
   primary remediation is switching the table to on-demand billing
   (the actual root cause). Raising the Lambda Timeout is secondary
   defence-in-depth, not the primary fix. A generic assistant inverts
   these priorities.

## Slash-command invocation

```
/aws:troubleshoot-lambda-invocation
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why fn-payments-webhook returns TaskTimeoutException"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: lambda-invocation-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the invocation success rate:

```bash
# Confirm the table is now on-demand
aws dynamodb describe-table --table-name orders-table --profile default \
  --query 'Table.BillingModeSummary'

# Confirm Lambda Duration drops below 5s p99
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=fn-payments-webhook \
  --start-time $(date -d '-30 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum \
  --profile default --output json

# Confirm no new WriteThrottleEvents on the table
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name WriteThrottleEvents \
  --dimensions Name=TableName,Value=orders-table \
  --start-time $(date -d '-30 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum \
  --profile default --output json
```

Then monitor the function's `Errors` metric for 1-2 hours to confirm
the TaskTimeoutException count drops to zero.
