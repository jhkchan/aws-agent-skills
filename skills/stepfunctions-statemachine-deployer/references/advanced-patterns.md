# Step Functions State Machine Deployer - advanced patterns (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Step 0: Expert knowledge - non-obvious Step Functions behaviors

These behaviors are easy to misjudge without operational Step Functions
experience. Each changes the architecture if ignored:

- **Standard bills per state transition; Express bills per invocation +
  duration.** Standard: $0.025 per 1,000 transitions. A 10-state workflow
  running 1M times/day = 10M transitions = $250/day. The same workload on
  Express at 100ms average duration = $1.00 per 1M invocations + ~$0.5/M
  GB-sec = ~$1.50/day. For high-volume idiomatic workloads, Express is
  ~100x cheaper. For long-running sagas, Standard is the only option.

- **Express at-least-once means Tasks MUST be idempotent.** Express
  workflows can retry a Task on internal failure — the integration is
  invoked MORE THAN ONCE. A non-idempotent Task (e.g., `dynamodb:PutItem`
  without idempotency key, or SQS SendMessage without dedup) produces
  duplicates. Standard does not have this issue (exactly-once).

- **Express execution history expires in 5 minutes (sync) or 1 hour
  (async).** Without `LoggingConfiguration.level: ALL` +
  `includeExecutionData: true`, an Express execution is forensic-black-hole
  after 5-60 minutes. Standard retains 90 days via API/console. This is
  why logging is a CRITICAL severity finding on Express.

- **`TracingConfiguration.enabled: true` is a NO-OP on Express.** The API
  accepts the field silently; no X-Ray traces are produced. Express
  distributed visibility uses CloudWatch Logs ServiceLens (weaker). Standard
  honors the field and emits full X-Ray segments per state transition.

- **A Task without explicit `TimeoutSeconds` defaults to 60 seconds.**
  Lambda functions configured with timeout > 60s are silently killed by
  Step Functions at 60s — the Lambda invocation continues (and bills) but
  the state advances to `States.Timeout`. Always set `TimeoutSeconds`
  based on the integration's expected runtime.

- **`HeartbeatSeconds` is REQUIRED for Activity-based Tasks.** A Task with
  `Resource: arn:aws:states:<region>:<account>:activity:<name>` relies on
  an external worker calling `GetActivityTask` + `SendTaskHeartbeat`.
  Without `HeartbeatSeconds`, a dead worker is not detected until
  `TimeoutSeconds` (potentially hours).

- **`Retry` and `Catch` are NOT interchangeable.** `Retry` re-executes the
  SAME state (for transient errors). `Catch` routes to a DIFFERENT state
  (the error handler). `Retry` without `Catch` still fails the execution
  if retries exhaust. `Catch` without `Retry` does not retry transient
  errors. Production Tasks require BOTH.

- **Default `Retry` parameters (IntervalSeconds=1, MaxAttempts=3,
  BackoffRate=2.0) are reasonable but should be explicit.** A `Retry`
  block with only `ErrorEquals` and no other fields uses these defaults.
  Make them explicit so reviewers can audit the backoff curve.

- **`MaxConcurrency: 0` on a Map means UNBOUNDED.** The default is 0, which
  means Step Functions invokes iterations as fast as possible. For >100
  items, this overwhelms downstream services (Lambda concurrency,
  DynamoDB throttling). Always set an explicit `MaxConcurrency`.

- **Inline Map caps at 40 concurrent iterations and 256KB total payload.**
  Beyond that, use Distributed Map. Distributed Map supports up to 10,000+
  concurrent iterations and reads directly from S3 or DynamoDB via
  `ItemReader` without loading items into the workflow payload.

- **Distributed Map runs under a SEPARATE child execution.** Each
  Distributed Map iteration is its own Step Functions execution with its
  own execution history. The parent workflow's `MaxConcurrency` controls
  child-execution fan-out. The child executions bill separately.

- **`.sync` waits for the integration to complete; the workflow is billed
  for the wait.** `arn:aws:states:::ecs:runTask.sync` blocks the Task until
  the ECS task finishes — the state transition is "in progress" for the
  task duration. On Standard, this is one transition (cheap); on Express,
  this counts against the 5-minute cap. Long ECS/Glue jobs on Express
  are impossible.

- **`.waitForTaskToken` pauses indefinitely (up to 1 year on Standard).**
  The Task returns a Task Token; the workflow pauses until an external
  worker calls `SendTaskSuccess` or `SendTaskFailure`. The Token is valid
  for 1 year on Standard, 5 minutes on Express (essentially unusable on
  Express for human-approval patterns).

- **`definition` is a STRING in the API, not a JSON object.**
  `CreateStateMachine` expects `"definition": "{\"StartAt\": ...}"`
  (stringified ASL). Terraform's `jsonencode()` handles this; raw
  CloudFormation requires `!Sub` with JSON-string escape. Passing a parsed
  object fails with `InvalidDefinition`.

- **`States.ALL` does NOT match `States.Timeout` in older runtime
  versions.** State machines created before November 2022 with
  `Catch: [{"ErrorEquals": ["States.ALL"]}]` miss the timeout path. For
  long-running production workflows, list `States.Timeout` explicitly
  alongside `States.ALL`.

- **The execution role's trust policy MUST include
  `states.amazonaws.com`.** `CreateStateMachine` does NOT validate the
  trust policy — it accepts any role ARN. At runtime, the first service
  integration fails with `AccessDenied`. Always verify the trust policy
  separately.

- **AWS SDK integrations allow direct API calls without Lambda.**
  `arn:aws:states:::aws-sdk:dynamodb:query` invokes the DynamoDB Query
  API directly — no Lambda glue code needed. This is the modern pattern
  for single-API-call Tasks. Resource ARN format:
  `arn:aws:states:::aws-sdk:<service>:<action>`.

- **Bedrock model invocation is a first-class integration.**
  `arn:aws:states:::bedrock:invokeModel` synchronously invokes a Bedrock
  model from a Task. The role needs `bedrock:InvokeModel` on the model
  ARN. Async invocation uses
  `arn:aws:states:::bedrock:invokeModel.sync` (Standard only).

- **RedriveExecution (November 2024) changes the recovery calculus for
  failed Standard executions.** A failed Standard execution can be
  redriven from the point of failure after fixing the definition — without
  re-running already-succeeded states. Express does NOT support redrive.
  Build Catch blocks that route to a state which can be safely re-run on
  redrive.

## Recent AWS features (2024-2026)

- **RedriveExecution (November 2024):** A failed Standard execution can
  be redriven from the point of failure after fixing the definition
  — without re-running already-succeeded states. Express does NOT support
  redrive. Build Catch blocks that route to states safe to re-run on
  redrive. `aws stepfunctions redrive-execution --execution-arn <arn>`.

- **Distributed Map enhancements (2024-2025):** Distributed Map now
  supports cross-account S3 sources, DynamoDB Scan/Query with filters,
  and `MaxItemsPerBatchPath` for dynamic batch sizing. Higher
  `MaxConcurrency` (10,000+) is now supported.

- **Step Functions Playground (2024-2025):** In-console ASL experimentation
  environment with live validation. Useful for prototyping, but production
  definitions should be deployed via IaC.

- **AWS SDK service integrations (2024-2025 expansion):** Direct API
  calls to ~140+ AWS services without Lambda glue code. Resource ARN:
  `arn:aws:states:::aws-sdk:<service>:<action>`. Modern preferred
  pattern for single-API Tasks (e.g.,
  `arn:aws:states:::aws-sdk:secretsmanager:GetSecretValue`).

- **Bedrock model invocation (2024-2025):** First-class integration via
  `arn:aws:states:::bedrock:invokeModel` (sync) and
  `arn:aws:states:::bedrock:invokeModel.sync` (Standard only, async).
  The role needs `bedrock:InvokeModel` on the model ARN. Enables GenAI
  orchestration (RAG pipelines, multi-step LLM flows) without Lambda.

- **Resource-based policies for state machines (2024-2025):** Cross-account
  state machine execution via resource-based policies. The deploying
  account can grant `states:StartExecution` to a cross-account principal.
  Verify such policies include `aws:SourceAccount` conditions.

- **Payload validation with JSON Schema (2024):** Step Functions accepts
  a JSON Schema for state-input validation. Add schemas on states
  receiving external input to prevent malformed data from propagating.

- **Variable policies and JSONata (Parsed 2024 features):** New ASL
  extensions for richer variable manipulation. Available on newly-created
  state machines; opt-in via the `StateMachineVersionName` field. Verify
  the runtime supports these features before depending on them.

