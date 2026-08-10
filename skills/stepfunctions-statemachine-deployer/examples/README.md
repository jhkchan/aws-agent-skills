# End-to-end usage scenario: stepfunctions-statemachine-deployer

A walkthrough showing the skill designing an Express sync state machine
that backs an API Gateway endpoint, including type selection rationale,
Retry/Catch shape, IAM scope derivation, and the mandatory logging
configuration. This exercises Step 1 (type selection), Step 3 (service
integrations), Step 6 (error handling), Step 8 (IAM role), and Step 9
(logging).

## Input (user prompt)

> Deploy an Express sync Step Functions state machine `checkout-express`
> in us-east-1 (account 111111111111) that backs an API Gateway endpoint.
> Workflow: ValidateCart Lambda (30s), ChargePayment Lambda (60s),
> UpdateOrderRecord via `aws-sdk:dynamodb:updateItem` on `OrdersTable`
> (30s), Succeed. ChargePayment needs Retry on `Lambda.ServiceException`
> and Catch `States.ALL` → PaymentErrorHandler. UpdateOrderRecord needs
> Retry on `DynamoDB.ProvisionedThroughputExceededException`. The role
> `checkout-sfn-role` exists with trust for `states.amazonaws.com`.
> Total runtime < 30 seconds.

## Skill output

```text
STATE_MACHINE_SPEC: checkout-express
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Name: checkout-express
  Type: EXPRESS (Synchronous — RequestResponse, invoked via API Gateway)
  Definition: StartAt=ValidateCart, 5 states (ValidateCart, ChargePayment,
    PaymentErrorHandler, UpdateOrderRecord, Succeed). All paths reach a
    terminal.
  Service integrations:
    - arn:aws:states:::lambda:invoke (ValidateCart, ChargePayment) — sync
      Lambda invocation
    - arn:aws:states:::aws-sdk:dynamodb:updateItem (UpdateOrderRecord) —
      direct DynamoDB API, no Lambda glue
  Map states: none
  Error handling:
    - ChargePayment: Retry on Lambda.ServiceException,
      Lambda.TooManyRequestsException (IntervalSeconds 2, MaxAttempts 3,
      BackoffRate 2.0) + Catch States.ALL → PaymentErrorHandler
      (ResultPath $.error)
    - UpdateOrderRecord: Retry on
      DynamoDB.ProvisionedThroughputExceededException (IntervalSeconds 5,
      MaxAttempts 5, BackoffRate 2.0)
    - All Tasks have explicit TimeoutSeconds (30, 60, 30)
  IAM role:
    - Trust: states.amazonaws.com (verified)
    - Identity policy: lambda:InvokeFunction on ValidateCartFn +
      ChargePaymentFn ARNs; dynamodb:UpdateItem on OrdersTable ARN;
      logs:CreateLogDelivery, logs:PutLogEvents, logs:DescribeLogGroups,
      logs:GetLogDelivery, logs:UpdateLogDelivery on log group ARN
  Logging: level=ALL, includeExecutionData=true → CloudWatch Logs
    (/aws/states/checkout-express) — mandatory for Express
  Tracing: TracingConfiguration.enabled NOT set (no-op on Express;
    ServiceLens provides partial visibility)
CHECKLIST:
  [x] Workflow type: EXPRESS — high-volume API Gateway backend, <5min
      total runtime, idempotency-safe Tasks
  [x] ASL definition validated — all paths reach Succeed or Fail
  [x] Every fallible Task has Retry AND Catch (ChargePayment,
      UpdateOrderRecord)
  [x] Every Task has explicit TimeoutSeconds (30, 60, 30)
  [x] Resource ARNs: bare lambda:invoke (Lambda is already sync),
      aws-sdk:dynamodb:updateItem (direct API)
  [x] IAM role scoped to 2 Lambda ARNs + 1 DynamoDB table ARN + log group
  [x] Trust policy: states.amazonaws.com verified
  [x] Express Logging: level=ALL + includeExecutionData=true
FINDINGS:
  - [INFO] Estimated cost at 10M invocations/day @ 100ms avg duration:
    $10/day invocation + ~$5/day GB-sec = ~$15/day (~$450/month)
  - [INFO] Idempotency: ChargePayment Lambda MUST be idempotent (Express
    at-least-once semantics). Verify the function uses an idempotency
    key (e.g., Stripe idempotency key derived from execution ARN +
    state name).
  - [INFO] No Distributed Map needed — payload well under 256KB
  - [WARN] Express sync via API Gateway: total workflow must complete in
    < 29 seconds (API Gateway 30s timeout). Current longest path
    ChargePayment (60s timeout) + UpdateOrderRecord (30s) = 90s — REDUCE
    ChargePayment TimeoutSeconds to 20s and UpdateOrderRecord to 5s OR
    accept that the API Gateway call will time out and rely on the async
    fallback path.
DEPLOY_COMMANDS:
  1. aws iam put-role-policy --role-name checkout-sfn-role \
       --policy-name Scoped --policy-document file://identity-policy.json
  2. aws logs create-log-group \
       --log-group-name /aws/states/checkout-express
  3. aws stepfunctions validate-state-machine-definition \
       --definition file://definition.json --type EXPRESS
  4. aws stepfunctions create-state-machine \
       --name checkout-express --definition file://definition.json \
       --type EXPRESS \
       --role-arn arn:aws:iam::111111111111:role/checkout-sfn-role \
       --logging-configuration level=ALL,includeExecutionData=true \
       --log-configuration-destinations \
         cloudWatchLogsLogGroupArn=arn:aws:logs:us-east-1:111111111111:log-group:/aws/states/checkout-express:*
```

## What the skill caught that a generic assistant misses

1. **Express type as a deliberate choice.** A generic assistant defaults
   to whatever type was mentioned without surfacing the trade-offs. The
   skill documents the cost/throughput rationale AND surfaces the
   at-least-once idempotency requirement that Express imposes on Tasks.

2. **Mandatory Express logging configuration.** A generic assistant
   omits `LoggingConfiguration`. The skill flags `level=ALL` +
   `includeExecutionData=true` as MANDATORY for Express (execution
   history expires in 5-60 minutes — without CloudWatch Logs there is
   NO durable forensic record).

3. **X-Ray is a no-op on Express.** A generic assistant may recommend
   `--tracing-configuration enabled=true`. The skill knows this field
   is silently accepted but produces no traces on Express and omits it
   intentionally, recommending CloudWatch ServiceLens instead.

4. **IAM policy derivation per integration.** The skill walks each
   Task's Resource ARN and emits the specific named actions on specific
   ARNs. A generic assistant often recommends `AmazonStepFunctionsFullAccess`
   which grants `states:*` on `*` — a privilege escalation vector.

5. **API Gateway 29s timeout constraint.** The skill surfaces the
   API Gateway timeout (30s wall clock minus 1s margin) as a WARN
   because the requested Task timeouts (60s + 30s = 90s) exceed the
   caller timeout — a subtle integration bug a generic assistant
   misses.

## Slash-command invocation

```
/aws:deploy-stepfunctions-statemachine
```

Or via the orchestrator:

```
/aws:pipeline
You: "Deploy an Express sync workflow for checkout — Lambda + DynamoDB, <30s"
```

The orchestrator emits `[Phase: Deploy | Skills routed:
stepfunctions-statemachine-deployer]` and hands off to this skill for
the VERDICT.

## Live-account deployment flow (optional, requires AWS CLI)

```bash
# 1. Verify the execution role exists and trusts states.amazonaws.com:
aws iam get-role --role-name checkout-sfn-role \
  --query 'Role.AssumeRolePolicyDocument.Statement[?Principal.Service==`states.amazonaws.com`]'

# 2. Apply the scoped identity policy to the role:
aws iam put-role-policy --role-name checkout-sfn-role \
  --policy-name Scoped --policy-document file://identity-policy.json

# 3. Create the CloudWatch Logs log group BEFORE create-state-machine:
aws logs create-log-group --log-group-name /aws/states/checkout-express

# 4. Validate the ASL definition:
aws stepfunctions validate-state-machine-definition \
  --definition file://definition.json --type EXPRESS

# 5. Create the state machine:
aws stepfunctions create-state-machine \
  --name checkout-express --definition file://definition.json \
  --type EXPRESS \
  --role-arn arn:aws:iam::111111111111:role/checkout-sfn-role \
  --logging-configuration level=ALL,includeExecutionData=true \
  --log-configuration-destinations \
    cloudWatchLogsLogGroupArn=arn:aws:logs:us-east-1:111111111111:log-group:/aws/states/checkout-express:*

# 6. Smoke-test via the Express Sync endpoint:
aws stepfunctions start-sync-execution \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:checkout-express \
  --input file://test-input.json
```
