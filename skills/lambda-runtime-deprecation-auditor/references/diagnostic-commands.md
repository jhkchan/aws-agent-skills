# Diagnostic Commands — Lambda Runtime Deprecation Auditor

Command listings moved verbatim from SKILL.md: multi-function sweep
pagination and the async-trigger detection sequence. Load on demand.

### Pre-flight — multi-function sweep note (pagination)

**Multi-function sweep note (pagination):** when auditing every function in
an account, `aws lambda list-functions` returns at most 50 per page. Use
`--marker` from the prior `NextMarker` to page through all functions. For
each function, also fetch `get-function-url-config` and `get-policy` —
both are separate API calls and silently return empty if the resource is
absent (no URL configured, no resource-based policy). Always drain
pagination to completion; the long tail of functions is most likely to be
stale, forgotten, and running a deprecated runtime.

### Step 4 — async-trigger detection algorithm (DLQ assessment)

  **Async-trigger detection algorithm (run this exact sequence):**
  1. `aws lambda list-event-source-mappings --function-name <name>` — if
     any mapping exists (SQS, DynamoDB Streams, Kinesis, MSK), the
     function is **polled** (not async-invoke, but still benefits from a
     DLQ for batch-failure scenarios with `FunctionResponseTypes`).
  2. Check `triggers` field or EventBridge: `aws events list-rule-targets-by-rule`
     — if the function ARN appears as a target, it is async-invoked.
  3. Check S3: `aws s3api get-bucket-notification-configuration` on
     relevant buckets — `LambdaFunctionConfigurations` = async.
  4. Check SNS: `aws sns list-subscriptions` for `Endpoint` = function ARN
     — async.
  5. If no event-source mapping, no EventBridge rule, no S3 notification,
     no SNS subscription, AND the only callers are API Gateway / Function
     URL / SDK `Invoke` → **synchronous-only**: DLQ not required, skip
     this check.
