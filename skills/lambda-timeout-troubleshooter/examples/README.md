# Example usage: lambda-timeout-troubleshooter

A walkthrough showing the skill diagnosing a TaskTimeoutException that
mimics a downstream-service outage, demonstrating the SDK retry storm
diagnosis (the most under-diagnosed timeout cause), the bursty-vs-
uniform pattern recognition, and the evidence-backed
ROOT_CAUSE_IDENTIFIED verdict.

## Input (user prompt)

> Our order-handler Lambda started failing after the 09:00 traffic
> peak. 60% of invocations now return TaskTimeoutException at exactly
> 30 seconds. Off-peak invocations complete in 2-4 seconds. We've been
> debugging this as a Lambda timeout issue for 45 minutes — please help
> us find the actual root cause.

```text
FunctionName: fn-prod-order-handler
Qualifier: prod (version 18)
Runtime: nodejs20.x
Timeout: 30
MemorySize: 512
Handler: index.handler
PackageType: Zip
VpcConfig: (none — function is not VPC-attached)
SnapStart: (not applicable — Node.js)
LastUpdateStatus: Successful (last update 3 days ago)

Recent log pattern (peak-hour timeouts):
  INFO  Putting item to orders-table (id=...)
  Retrying request ... attempt 2 of 3
  Retrying request ... attempt 3 of 3
  (no further log line)
  END RequestId: ... Duration: 30000.00 ms
    Memory Size: 512 MB Max Memory Used: 142 MB
  Task timed out after 30.00 seconds

CloudWatch metrics (last hour):
  - Duration p50: 2.1s (off-peak), p99: 30s (peak), Maximum: 30s
  - MemoryUtilization Maximum: 28%
  - Errors: 142 (correlated with traffic peak)

DynamoDB context:
  - Table orders-table
  - BillingModeSummary: PROVISIONED
  - WriteCapacityUnits: 200
  - WriteThrottleEvents (last hour): sustained during peak
```

## Skill output

```text
TARGET: fn-prod-order-handler (alias: prod, version 18)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: AWS SDK v3 default maxRetries: 3 with exponential backoff on
  a DynamoDB call where the table is throttled (200 WCU on 5000 WCU
  demand). Each of the 3 attempts takes ~9s (the SDK requestTimeout
  default); total wall clock per invocation is ~28s against a 30s
  Lambda Timeout. Logs show "Retrying request ... attempt 2 of 3" and
  "attempt 3 of 3" before each kill. The off-peak invocations succeed
  because the table isn't throttled; the peak-hour failures are caused
  by the retry multiplier exhausting the budget on a throttled
  downstream.
LAYER: TIMEOUT_SDK_RETRY_STORM
EVIDENCE:
  - Symptom: 60% of invocations time out at exactly 30s during the
    09:00 traffic peak; off-peak invocations complete in 2-4s. The
    bursty pattern correlates with DynamoDB throttling, not with a
    uniform config-only timeout.
  - Probe: aws logs filter-log-events returns "Retrying request ...
    attempt 2 of 3" preceding 87% of "Task timed out" entries in the
    last hour.
  - Probe: aws cloudwatch get-metric-statistics on aws/dynamodb
    WriteThrottleEvents for orders-table returns sustained throttling
    in the same hour.
  - Probe: aws cloudwatch Duration Maximum == 30000 on the failing
    invocations; p50 is 2.1s (off-peak), p99 is 30s (peak).
  - Passing: MemoryUtilization Maximum = 28% (not OOM); SnapStart n/a
    (Node.js); no VPC attachment (not a network issue); no HTTP client
    call (not an axios/fetch hang); the function code is unchanged
    from the working off-peak version.
REMEDIATION:
  1. Set SDK maxAttempts: 0 in the DynamoDB client constructor so the
     function makes exactly one attempt and returns the throttling
     error to the caller for Lambda-level retry:
     const ddb = new DynamoDBClient({ maxAttempts: 0 });
  2. Switch the table to on-demand billing to absorb the burst:
     aws dynamodb update-table --table-name orders-table \
       --billing-mode PAY_PER_REQUEST --profile <p>
  3. Optionally raise Lambda Timeout to 60s as defence-in-depth
     against transient spikes:
     aws lambda update-function-configuration --function-name \
       fn-prod-order-handler --timeout 60 --profile <p>
  4. Verify by re-invoking during the next peak window; Duration
     Maximum should drop below 5s and Errors should drop to zero.
CONFIRM: Before updating the table or function, emit and await:
  "CONFIRM: About to switch orders-table to PAY_PER_REQUEST and update
   fn-prod-order-handler SDK maxAttempts. Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Recognised the SDK retry multiplier.** A generic assistant sees
   "Lambda times out at 30s calling DynamoDB" and says "raise the
   timeout" or "fix the table." The skill reads the log lines
   "Retrying request ... attempt 2 of 3" and "attempt 3 of 3" and
   identifies the SDK default `maxRetries: 3` as the budget consumer.
   The retry multiplier (3 attempts at ~9s each plus backoff) is
   consuming 28s of the 30s budget.

2. **Distinguished bursty from uniform timeout.** A config timeout
   affects every invocation uniformly. The bursty pattern (60% peak,
   0% off-peak) indicates a load-dependent cause — either downstream
   throttling or the retry multiplier on a throttled downstream. The
   skill's first probe cross-references DynamoDB `WriteThrottleEvents`
   against the Lambda `Duration` Maximum.

3. **Identified the dual root cause.** The skill names both the
   proximate cause (SDK retry multiplier exhausting the budget) and
   the underlying cause (DynamoDB throttling due to under-provisioned
   WCU). Remediation addresses both: disable SDK retries AND raise the
   table capacity.

4. **Ruled out memory, init, VPC, and HTTP client with positive
   evidence.** `MemoryUtilization Maximum: 28%` rules out OOM-before-
   timeout. `SnapStart: n/a (Node.js)` rules out init-phase timeout.
   `VpcConfig: (none)` rules out VPC ENI latency. The absence of an
   HTTP client call in the function code rules out axios/fetch hangs.

5. **Recommended disabling SDK retries, not just raising the timeout.**
   A generic assistant says "raise the timeout to 60s" — which doubles
   the per-invocation cost without addressing the retry multiplier
   (3 attempts at 9s each = 27s, fitting in 60s but still 9x the
   steady-state latency). The skill recommends `maxAttempts: 0` so
   the function makes one attempt and returns the error for Lambda-
   level retry handling.

## Slash-command invocation

```
/aws:troubleshoot-lambda-timeout
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why fn-prod-order-handler times out at 30s during peak"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: lambda-timeout-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the timeout resolution:

```bash
# Confirm the table is now on-demand
aws dynamodb describe-table --table-name orders-table --profile default \
  --query 'Table.BillingModeSummary'

# Confirm Lambda Duration drops below 5s p99
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=fn-prod-order-handler \
  --start-time $(date -d '-30 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics p99,Maximum \
  --profile default --output json

# Confirm no new WriteThrottleEvents on the table
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name WriteThrottleEvents \
  --dimensions Name=TableName,Value=orders-table \
  --start-time $(date -d '-30 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum \
  --profile default --output json

# Confirm the SDK is no longer retrying (no "Retrying request" entries)
aws logs filter-log-events \
  --log-group-name /aws/lambda/fn-prod-order-handler \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"Retrying request"' \
  --profile default --output json
```

Then monitor the function's `Errors` metric for 1-2 hours during the
next peak window to confirm the TaskTimeoutException count drops to
zero.
