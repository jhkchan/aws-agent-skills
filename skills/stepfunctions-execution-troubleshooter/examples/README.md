# End-to-end usage scenario: stepfunctions-execution-troubleshooter

A walkthrough showing the skill diagnosing a Step Functions
`States.Runtime` failure caused by a JSONPath mismatch. This exercises
Step 0 (signal capture), Step 1 (symptom categorisation), Step 2
(RUNTIME_ERROR walk), the root-cause catalog, and the remediation
workflow.

## Input (user prompt)

> Our `order-pipeline` Standard workflow in `us-east-1` is failing on
> every execution with `States.Runtime` on the `EnrichOrder` state.
> The `cause` says "An error occurred while executing the state
> 'EnrichOrder'." The input to `EnrichOrder` (from execution history)
> is `{ "orderId": "ord-123", "customerId": "cust-9" }` but the state
> definition has `"OrderId.$": "$.order.orderId"`. The Lambda
> `enrich-fn` was never invoked.

## Skill output

```text
INCIDENT: arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline
 / arn:aws:states:us-east-1:111111111111:execution:order-pipeline:abc —
 States.Runtime on EnrichOrder
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: RUNTIME_ERROR — EnrichOrder state's Parameters references
"OrderId.$": "$.order.orderId" but the actual input payload has the
field at "$.orderId" (no nested object). The JSONPath does not resolve
at runtime.
EVIDENCE:
  - describe-execution: status FAILED, error "States.Runtime", cause
    "An error occurred while executing the state 'EnrichOrder'."
  - get-execution-history StateEntered for EnrichOrder: input
    { "orderId": "ord-123", "customerId": "cust-9" }
  - describe-state-machine EnrichOrder Parameters:
    { "OrderId.$": "$.order.orderId",
      "Customer.$": "$.customerId",
      "FunctionName": "enrich-fn" }
  - Lambda enrich-fn CloudWatch Logs: zero invocations (function
    never reached — failure was at JSONPath resolution before invoke)
ROOT_CAUSE_CATALOG: #1 (invalid JSONPath in Parameters)
REMEDIATION:
  1. Update the EnrichOrder Parameters to reference the actual path:
     "OrderId.$": "$.orderId"
     Leave "Customer.$": "$.customerId" as-is (that path resolves
     correctly).
  2. Validate the fix via the TestState API before deploying:
     aws stepfunctions test-state \
       --definition '<fixed EnrichOrder ASL>' \
       --role-arn arn:aws:iam::111111111111:role/sfn-role \
       --input file://test-input.json \
       --query '{status:status,output:output,error:error}'
     Expect: status SUCCEEDED, no error.
  3. Update the state machine:
     aws stepfunctions update-state-machine \
       --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline \
       --definition file://fixed-asl.json \
       --role-arn arn:aws:iam::111111111111:role/sfn-role
  4. Run a verification execution:
     aws stepfunctions start-execution \
       --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline \
       --name verification-$(date +%s) \
       --input file://test-input.json
  5. Monitor CloudWatch ExecutionsFailed for the state machine; expect
     zero failures over the next hour of normal traffic.
```

## What the skill caught that a generic assistant misses

1. **The `error` vs `cause` distinction.** A generic assistant often
   treats `States.Runtime` as the root cause. The skill recognises
   that `States.Runtime` is the category; the `cause` names the state,
   and the actual root cause is in the ASL Parameters JSONPath.

2. **The never-invoked-Lambda signature.** A generic assistant might
   suggest checking the Lambda function. The skill notes that the
   Lambda has zero invocations because the failure occurs at JSONPath
   resolution before the integration is called — so the Lambda is
   irrelevant to this diagnosis.

3. **The TestState API verification step.** A generic assistant
   typically recommends updating the state machine and re-running.
   The skill inserts a `test-state` verification step that catches the
   fix (or a typo) without deploying.

4. **The "leave Customer.$ alone" note.** A generic assistant might
   suggest rewriting the entire Parameters block. The skill identifies
   that `Customer.$: $.customerId` is correct and should not be
   touched — only the offending path needs to change.

## Slash-command invocation

```
/aws:troubleshoot-stepfunctions-execution
```

Or via the orchestrator:

```
/aws:pipeline
You: "order-pipeline failing with States.Runtime on EnrichOrder"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
stepfunctions-execution-troubleshooter]` and hands off to this skill
for the VERDICT.

## Live-account diagnostic flow (requires AWS CLI)

When the operator has credentials for the failing account:

```bash
# Identify the most recently failed execution.
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline \
  --status FAILED --max-results 1

# Read the full error + cause.
aws stepfunctions describe-execution \
  --execution-arn arn:aws:states:us-east-1:111111111111:execution:order-pipeline:<id> \
  --query '{status:status,error:error,cause:cause}'

# Read the failing state's input from execution history.
aws stepfunctions get-execution-history \
  --execution-arn arn:aws:states:us-east-1:111111111111:execution:order-pipeline:<id> \
  --query 'events[?type==`StateEntered` && stateEnteredEventDetails.name==`EnrichOrder`].stateEnteredEventDetails.input' \
  --output text

# Read the failing state's ASL definition.
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline \
  --query 'definitionString' --output text \
  | jq '.States.EnrichOrder'
```

If the failing state's `Parameters` JSONPath does not match the input
shape from `StateEntered`, the diagnosis is confirmed without needing
to read the Lambda logs. The fix is to align the ASL path with the
actual payload shape.
