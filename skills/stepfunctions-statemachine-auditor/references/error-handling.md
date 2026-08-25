# Step Functions State Machine Auditor - error handling and remediation (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Remediation guidance (per verdict)

### For OVERPERMISSIVE_ROLE — wildcard or broad execution role

1. **Inventory the definition's service integrations.** Parse each `Task`
   state's `Resource` ARN to identify the exact actions + resources the
   workflow needs.
2. **Generate a scoped policy** granting only those actions on those ARNs.
   Use IAM Access Analyzer policy generation or build manually.
3. **Replace the broad policy:**
   ```
   aws iam put-role-policy --role-name <role> --policy-name Scoped \
     --policy-document file://scoped-policy.json --profile <p>
   ```
4. **For `states:StartExecution` on `*`:** scope to the specific state
   machine ARNs the workflow is permitted to chain into. If self-chaining
   is intended, scope to the workflow's own ARN only.
5. **Verify the trust policy** includes
   `Principal: { Service: "states.amazonaws.com" }`.

### For NO_LOGGING — missing or partial execution logging

1. **Set logging to ALL with execution data:**
   ```
   aws stepfunctions update-state-machine --state-machine-arn <arn> \
     --logging-configuration level=ALL,includeExecutionData=true \
     --profile <p>
   ```
2. **Verify the execution role has logging permissions:**
   `logs:CreateLogDelivery`, `logs:GetLogDelivery`,
   `logs:UpdateLogDelivery`, `logs:DeleteLogDelivery`,
   `logs:DescribeLogGroups`, `logs:PutLogEvents`.
3. **For Express workflows:** this is the ONLY durable record. Treat as
   incident-response priority — without logs, failed Express executions
   are irretrievable after 5-60 minutes.

### For NO_TRACING — missing or ineffective X-Ray tracing

1. **For Standard workflows:** enable tracing:
   ```
   aws stepfunctions update-state-machine --state-machine-arn <arn> \
     --tracing-configuration enabled=true --profile <p>
   ```
2. **Verify the role grants `xray:PutTraceSegments` +**
   `xray:PutTelemetryRecords`. Add if missing.
3. **For Express workflows:** X-Ray via `TracingConfiguration` is a no-op.
   Use CloudWatch Logs ServiceLens for partial distributed visibility.
   Migrate to Standard if full X-Ray tracing is a hard requirement.

### For CONFIG_GAP — definition or error-handling gap

1. **Missing Catch/Retry on a fallible Task:** add a `Catch` block matching
   `States.ALL` (broadest fallback) routing to an error-handler state, and
   a `Retry` block for known-transient errors:
   ```json
   "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ErrorHandler"}],
   "Retry": [{"ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"], "IntervalSeconds": 2, "MaxAttempts": 3, "BackoffRate": 2.0}]
   ```
2. **Missing `TimeoutSeconds`:** add an explicit value based on the
   integration's expected runtime (e.g., 30 for a fast Lambda, 300 for
   Glue, 3600 for long ECS tasks).
3. **Missing `HeartbeatSeconds` on Activity Tasks:** set
   `HeartbeatSeconds` < `TimeoutSeconds` (e.g., heartbeat 30, timeout 300).
4. **Unreachable states:** remove them or wire them into the `StartAt`
   chain. Dead states accumulate drift and confuse future maintainers.
5. **Choice without Default:** add a `Default` branch routing to a safe
   fallback or `Fail` state.
6. **Validate before pushing:**
   ```
   aws stepfunctions validate-state-machine-definition --definition file://def.json --type STANDARD
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend periodic review of the execution role as new service
   integrations are added to the definition.
3. Recommend a CloudWatch alarm on `ExecutionsFailed` > threshold for
   early detection of runtime issues logging alone would not surface.

