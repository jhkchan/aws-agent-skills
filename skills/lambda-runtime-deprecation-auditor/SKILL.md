---
name: lambda-runtime-deprecation-auditor
description: >-
  Audits AWS Lambda functions for deprecated/EOL runtimes (python3.9,
  nodejs16.x, etc.), over-permissioned execution roles (admin wildcards,
  privilege-escalation actions), public function URL exposure (AuthType
  NONE), and observability config gaps (missing X-Ray tracing, missing DLQ,
  log retention). Emits a deterministic verdict (DEPRECATED_RUNTIME |
  OVERPERMISSIVE | PUBLIC_EXPOSURE | CONFIG_GAP | OK) per function with
  enumerated findings and CLI remediation. Use when reviewing Lambda
  functions, checking runtime deprecation status, auditing execution-role
  scope, validating function-URL exposure, or hardening Lambda posture
  before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config-document classification.
  Live-account audits use aws lambda get-function, get-function-url-config,
  get-policy, and list-functions (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Lambda
  - runtime deprecation
  - EOL runtime
  - python3.9
  - nodejs16
  - deprecated runtime
  - execution role
  - over-permissive
  - AdministratorAccess
  - function URL
  - AuthType NONE
  - public exposure
  - X-Ray tracing
  - TracingConfig
  - PassThrough
  - Active tracing
  - dead letter queue
  - DLQ
  - Lambda audit
  - serverless security
  - runtime block
  - function hardening
tags: [lambda, security, runtime-deprecation, execution-role, function-url, tracing, audit, compute]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Compute
  verdict_shape: "DEPRECATED_RUNTIME | OVERPERMISSIVE | PUBLIC_EXPOSURE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a Lambda function before production deployment, checking for
    deprecated or EOL runtimes, auditing an execution role for wildcard
    permissions, validating function-URL public exposure, or hardening
    observability configuration (tracing, DLQ, log retention) across a
    serverless fleet.
  activation_triggers:
    - "audit this Lambda function"
    - "is my Lambda runtime deprecated"
    - "check Lambda execution role"
    - "is my function URL public"
    - "Lambda AuthType NONE"
    - "missing X-Ray tracing Lambda"
    - "Lambda runtime EOL"
    - "hardening Lambda function"
    - "Lambda admin role"
  invocation_schema: >-
    Input: either (a) a Lambda function configuration (Runtime, Handler,
    TracingConfig, DeadLetterConfig, Execution role + policies, Function URL
    config), OR (b) a function name/ARN for live-account audit.
    Output: deterministic FUNCTION/VERDICT/REASON/FINDINGS/REMEDIATION block
    per function, where VERDICT ∈ {DEPRECATED_RUNTIME, OVERPERMISSIVE,
    PUBLIC_EXPOSURE, CONFIG_GAP, OK}. ERROR is emitted only for malformed
    input and is not a classification verdict.
---

# Lambda Runtime Deprecation Auditor

## Quick start (5-line audit)

1. **Runtime:** Is `Runtime` in the supported set (Step 1 table)? If no →
   **DEPRECATED_RUNTIME**. If `PackageType: Image`, skip — runtime is in the
   container, not the metadata.
2. **Function URL:** Is `AuthType: NONE`? If yes → **PUBLIC_EXPOSURE**.
3. **Execution role:** Any `Action: "*"` on `"*"`? Any service wildcard
   (`s3:*`, `iam:*`) on `"*"`? If yes → **OVERPERMISSIVE**.
4. **Config:** `TracingConfig: PassThrough`? Missing DLQ on an async function?
   `ReservedConcurrentExecutions: 0`? If yes → **CONFIG_GAP**.
5. **Aggregate:** Worst finding wins:
   DEPRECATED_RUNTIME > PUBLIC_EXPOSURE > OVERPERMISSIVE > CONFIG_GAP > OK.

All four dimensions are evaluated independently; the verdict is always the
worst. Skip to [Quick reference](#quick-reference--verdict-thresholds) for
the full matrix or [Process](#process--classification-logic-apply-in-order-aggregate-worst)
for the ordered steps.

### Input schema (formal)

The auditor accepts either a function name/ARN (live-account mode) or a
configuration object (offline-classification mode).

**Live-account mode** — provide the function identifier:

```json
{
  "function_identifier": "my-lambda-function",
  "account_id": "123456789012",
  "region": "us-east-1"
}
```

**Offline-classification mode** — provide the configuration object as
returned by `aws lambda get-function-configuration --output json`:

```json
{
  "function_name": "my-lambda-function",
  "runtime": "python3.9",
  "package_type": "Zip",
  "architectures": ["x86_64"],
  "role_arn": "arn:aws:iam::123456789012:role/my-exec-role",
  "attached_policies": [
    {"type": "managed", "name": "AWSLambdaBasicExecutionRole"},
    {"type": "inline", "name": "my-inline", "document": {"Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}]}}
  ],
  "tracing_config": {"Mode": "PassThrough"},
  "dead_letter_config": null,
  "reserved_concurrent_executions": null,
  "function_url_config": {"AuthType": "NONE"},
  "resource_based_policy": null,
  "last_modified": "2025-03-15T10:00:00.000Z",
  "event_source_mappings": [],
  "triggers": ["eventbridge"]
}
```

**Required fields for offline mode:** `function_name`, `runtime`,
`package_type`, `role_arn`, `attached_policies`, `tracing_config`.
All others are optional but recommended for a complete audit.

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
all dimensions, and a deprecated runtime is the highest-priority finding —
not because it is a security vulnerability, but because AWS **will disable
the function** on a fixed timeline. A function on python3.9 is not "stale";
it is a ticking time bomb whose fuse AWS controls.

Lambda configuration posture spans four independent dimensions:

- **Runtime lifecycle** — AWS deprecates and then **blocks** runtimes on a
  published schedule. Phase 1 blocks creates/updates; Phase 2 **disables
  invocations entirely**. A deprecated function that you cannot update is
  one deployment away from permanent breakage.
- **Execution-role scope** — the role is the function's blast radius. A
  function with `Action: "*" Resource: "*"` is a privilege-escalation
  springboard if the handler is ever compromised.
- **Public exposure** — a Function URL with `AuthType: NONE` lets **anyone
  on the internet** invoke the function. No IAM, no signing, no rate-limit
  beyond account concurrency.
- **Observability gaps** — `TracingConfig: PassThrough` means no X-Ray
  traces unless the caller sends the X-Ray header (most external callers
  do not). Missing DLQs silently swallow async failures.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Runtime is NOT in the supported-runtime set (deprecated/EOL) | **DEPRECATED_RUNTIME** | Step 1 |
| Function URL `AuthType: NONE` (publicly invocable) | **PUBLIC_EXPOSURE** | Step 2 |
| Execution role grants `Action: "*"` on `Resource: "*"` (admin) | **OVERPERMISSIVE** | Step 3 |
| Execution role grants privilege-escalation service wildcard (`iam:*`, `sts:*`, etc.) on `"*"` | **OVERPERMISSIVE** | Step 3 |
| Execution role grants any service wildcard (`s3:*`, `dynamodb:*`) on `"*"` | **OVERPERMISSIVE** | Step 3 |
| `TracingConfig.Mode: PassThrough` (no active tracing) | **CONFIG_GAP** | Step 4 |
| Missing DeadLetterConfig on an async-invoked function | **CONFIG_GAP** | Step 4 |
| All dimensions clean (current runtime, scoped role, no public URL, tracing active) | **OK** | Step 5 |
| `PackageType: Image` (container function) | Runtime check is **N/A** — skip Step 1 | Pre-flight |

Verdict priority (worst finding wins):
DEPRECATED_RUNTIME > PUBLIC_EXPOSURE > OVERPERMISSIVE > CONFIG_GAP > OK.

## Pre-flight: function metadata gate (run before classification)

Before evaluating the function configuration, classify the function
itself. Several attributes **short-circuit** the audit — misclassifying
them produces false positives.

**Multi-function sweep note (pagination):** when auditing every function in
an account, `aws lambda list-functions` returns at most 50 per page. Use
`--marker` from the prior `NextMarker` to page through all functions. For
each function, also fetch `get-function-url-config` and `get-policy` —
both are separate API calls and silently return empty if the resource is
absent (no URL configured, no resource-based policy). Always drain
pagination to completion; the long tail of functions is most likely to be
stale, forgotten, and running a deprecated runtime.

| Attribute | Value | Effect on audit |
|---|---|---|
| `PackageType` | `Image` | **Container-image function.** The `Runtime` field is empty — the runtime is baked into the container image. Skip Step 1 (runtime lifecycle). Still audit the role (Step 3), URL (Step 2), and config (Step 4). Flag that runtime CVEs must be checked via container-image scanning, not Lambda metadata. |
| `PackageType` | `Zip` | Proceed with full audit including runtime check. |
| `Runtime` | `provided.al2023` | **Custom runtime on Amazon Linux 2023.** This is current. Do NOT flag as deprecated. The runtime string is user-managed, not AWS-managed — deprecation tracking is the operator's responsibility. |
| `Runtime` | `provided.al2` | **Custom runtime on Amazon Linux 2.** AL2 is approaching EOL (mid-2026). Flag as CONFIG_GAP (stale base OS), not DEPRECATED_RUNTIME — AWS has not deprecated the runtime identifier itself. |
| `Runtime` | `provided` | **Original custom runtime (Amazon Linux 1).** AL1 is fully EOL. Treat as DEPRECATED_RUNTIME — the base OS receives no security patches. |
| `Architectures` | `arm64` | Graviton. Most current runtimes support arm64. Older runtimes (nodejs12.x, python3.7) do not — a deprecated runtime on arm64 is doubly broken. |
| `State` | `Inactive` | Function is not invocable. Note as operational finding but not a security verdict driver unless combined with other findings. |

**If the function configuration is malformed** (missing `Runtime` on a Zip
function, missing `Role`, invalid JSON for policies), output:

```text
FUNCTION: <name>
VERDICT: ERROR
REASON: Function configuration is incomplete or malformed — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws lambda get-function-configuration --function-name <name> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Lambda behaviors that change classification

These behaviors are easy to misjudge without operational Lambda
experience. Each changes a verdict if ignored:

- **Runtime deprecation has two phases, not one.** Phase 1 (deprecation
  date): you can no longer **create** new functions or **update** existing
  ones with this runtime. Existing functions still **execute** normally.
  Phase 2 (block date, typically ~30+ days after Phase 1): the function is
  **disabled** — invocations return `Runtime.UnsupportedException`. A
  function in Phase 1 is a time bomb; a function in Phase 2 is an active
  outage. Both produce DEPRECATED_RUNTIME, but the FINDINGS text should
  state which phase applies.

- **`PackageType: Image` functions have NO runtime field.** The runtime is
  baked into the container image's base layer. The Lambda API returns
  `Runtime: null` for these functions. Flagging this as "missing runtime"
  is a false positive — the runtime check (Step 1) does not apply. To
  audit the runtime of a container function, inspect the container image
  registry (ECR) and scan the image for OS/package CVEs. This is outside
  the Lambda API surface.

- **`provided.al2023` is NOT a deprecated runtime.** It is the current
  custom-runtime identifier on Amazon Linux 2023. AWS does not track
  deprecation for `provided.*` identifiers — the operator manages the
  runtime version inside the bootstrap binary. Do NOT flag
  `provided.al2023` as deprecated. `provided.al2` (Amazon Linux 2) is
  approaching OS EOL and should be flagged as CONFIG_GAP. `provided`
  (Amazon Linux 1, fully EOL) should be flagged as DEPRECATED_RUNTIME.

- **A Function URL with `AuthType: NONE` bypasses IAM entirely.** Unlike
  API Gateway (which can use IAM auth, Cognito, Lambda authorizers, or
  no auth), a Function URL with `NONE` is a single DNS name that anyone
  can POST to. There is no WAF, no rate-limiter, no request validation
  between the caller and your handler. The only protection is Lambda
  throttling/concurrency limits. This is why PUBLIC_EXPOSURE outranks
  OVERPERMISSIVE in the verdict priority — the function is reachable by
  the entire internet, regardless of the role's scope.

- **`TracingConfig: PassThrough` is effectively "no tracing" for most
  functions.** In PassThrough mode, X-Ray records a trace segment ONLY if
  the incoming request carries an `X-Amzn-Trace-Id` header. API Gateway
  injects this header, but direct invocations (EventBridge, S3 triggers,
  CLI, SDK) typically do not. For a function triggered by anything other
  than API Gateway, PassThrough produces zero traces. Only `Active` mode
  guarantees trace recording.

- **The execution role's effective permissions include ALL attached
  policies** — managed (AWS and customer), inline, and permissions
  boundaries. A function with a scoped inline policy but
  `AdministratorAccess` as a managed policy is still OVERPERMISSIVE. When
  auditing, enumerate `list-attached-role-policies` AND
  `list-role-policies` (inline). Checking only inline policies misses the
  most common over-permission pattern: attaching a broad AWS-managed
  policy for convenience.

- **`lambda:InvokeFunction` in a resource-based policy with `Principal:
  "*"` is NOT the same as a Function URL.** A resource-based policy grants
  InvokeFunction to any AWS principal (who must still have IAM credentials
  and `sts:GetCallerIdentity`). A Function URL with `AuthType: NONE` grants
  invocation to anyone with a URL — no AWS account required. The former is
  a same-account/cross-account IAM concern; the latter is a public
  exposure. Both are findings, but they classify differently.

- **`SnapStart` is only available on `java17` and `java21`.** If a
  function has `SnapStart: Active` on a non-Java runtime, the
  configuration is invalid and the function will fail to create/update.
  This is a misconfiguration, not a deprecation finding.

- **`go1.x` is a versionless runtime — it never deprecates.** Unlike
  python3.x or nodejsN.x which track a specific language version, `go1.x`
  always uses the latest Go release at invocation time. AWS handles the
  Go binary update transparently. Do NOT flag `go1.x` as deprecated — it
  has no deprecation schedule. The trade-off is that Go code compiled
  against an older standard library may break when the runtime Go version
  is bumped (rare but possible for CGO-dependent code). Note this in
  FINDINGS if the function uses CGO.

- **Lambda encrypts environment variables at rest with a KMS key.** By
  default, Lambda uses an AWS-managed KMS key (`aws/lambda`). If the
  function uses a customer-managed KMS key (`KMSKeyArn` field), the
  execution role must have `kms:Decrypt` on that key ARN — otherwise the
  function fails at init with `KMS.DecryptException`. A customer-managed
  key with a cross-account policy is a secondary exposure vector.

- **`AWSLambdaBasicExecutionRole` is the minimum-safe managed policy.**
  It grants `logs:CreateLogGroup`, `logs:CreateLogStream`, and
  `logs:PutLogEvents` — nothing else. If the execution role has ONLY this
  managed policy, it is least-privilege for logging. The common mistake
  is attaching `AWSLambdaVPCAccessExecutionRole` (adds `ec2:Create*`,
  `ec2:Describe*`) when the function does NOT run in a VPC — the extra
  EC2 permissions are unnecessary and widen the blast radius.

- **Determining async-invoked functions for DLQ assessment.** To decide
  whether a missing DLQ is a CONFIG_GAP, check the event-source mapping
  and trigger configuration: `aws lambda list-event-source-mappings
  --function-name <name>` returns SQS/DynamoDB Streams/Kinesis mappings
  (these are polling triggers, not async). EventBridge rules, S3 event
  notifications, and SNS subscriptions invoke asynchronously. API
  Gateway, Function URLs, and SDK `Invoke` calls are synchronous. Only
  async-invoked functions need a DLQ — the retry+discard behavior does
  not apply to sync invocations (the caller gets the error directly).

- **`LastModified` older than 180 days on a deprecated runtime is an
  elevated risk.** A function that has not been touched in 6+ months is
  likely forgotten. When the runtime reaches Phase 2, the team will not
  have a deployment pipeline ready to update it. Surface the stale
  `LastModified` date in the FINDINGS text for any deprecated runtime — it
  determines whether the fix is a quick runtime bump or a full code
  revival effort.

- **Reserved concurrent executions set to 0 is a silent kill switch.**
  The function exists and appears healthy, but all invocations are
  throttled. This is either an intentional cost-control measure or an
  accidental misconfiguration. Flag as CONFIG_GAP with the note that the
  function is effectively disabled.

**Proprietary heuristics — go/no-go thresholds the AWS docs do not publish:**

- **Deprecation Urgency Composite Score (DUCS).** Combine three factors
  into a 0–10 urgency score to prioritize migration order across a fleet:
  (a) Phase — Phase 1 = 2 pts, Phase 2 = 4 pts (function already broken);
  (b) LastModified staleness — <90 days = 0, 90–180 = 1, 180–365 = 2,
  >365 = 3 (a forgotten function has no ready deployment pipeline);
  (c) Event-source-mapping dependency — has SQS/Kinesis/DynamoDB Streams
  pollers = +2 (Phase 2 silently breaks the downstream pipeline with no
  error surfaced to the caller); sync-only = +0. **Score ≥7 →
  "emergency: re-platform before next deploy window." 4–6 →
  "schedule this sprint." ≤3 → "routine, batch with next code change."**
  This score is the auditor's own threshold — AWS publishes no equivalent.
  Surface it in FINDINGS text as a parenthetical: `(DUCS: 7/10 —
  emergency)`.

- **Runtime migration breaking-change probability matrix.** Not every
  upgrade is equal. Map each common path to its known breakage class so
  the remediation section carries an honest warning, not just a CLI
  command: `python3.9→3.12` — distutils + imp + asyncore removed
  (HIGH: re-test packaging, `importlib` migrations);
  `python3.9→3.13` — all 3.12 breakages + PEP 563 deferred annotation
  evaluation (MED: type-hint-dependent frameworks may need
  `from __future__ import annotations`);
  `nodejs16.x→20.x` — OpenSSL 3.x upgrade (MED: crypto calls that worked
  with legacy providers throw `ERR_OSSL_EVP_UNSUPPORTED`; fix with
  `--openssl-legacy-provider` as interim, then re-test);
  `nodejs18.x→22.x` — V8 12.x, removed `url.parse()` legacy paths (LOW);
  `java8→java17` — `javax.*`→`jakarta.*` namespace migration (HIGH for
  any EE/JAX-WS dependency; `javax.xml.bind` must be replaced);
  `java17→java21` — virtual threads can break `ThreadLocal` + pinning
  on `synchronized` blocks (MED: load-test before enabling). Append
  the relevant breakage class to REMEDIATION step 2 as a mandatory
  pre-test checkpoint.

- **Execution role blast-radius tier (not binary).** Go beyond
  pass/fail — classify the role into four tiers that drive the
  remediation urgency: **Tier 0** (LEAST PRIVILEGE): named actions on
  specific ARNs, no wildcards — safe. **Tier 1** (SCOPED WILDCARD):
  service-scoped action or resource wildcard but not both (`s3:Get*` on
  a named bucket) — acceptable, note in FINDINGS. **Tier 2** (BROAD):
  service wildcard on `"*"` (`dynamodb:*` on `"*"`) — OVERPERMISSIVE.
  **Tier 3** (CRITICAL): any of `Action: "*"` on `"*"`, `iam:PassRole`
  on `"*"`, or `sts:AssumeRole` on `"*"` — immediate privesc springboard;
  flag in FINDINGS with `[OVERPERMISSIVE-CRITICAL]` prefix and recommend
  Access Analyzer policy generation before the next deploy. The tier
  appears as a suffix on the verdict line:
  `VERDICT: OVERPERMISSIVE (Tier 3 — CRITICAL)`.

### Step 1: Runtime lifecycle evaluation (highest priority — operational time bomb)

Compare the `Runtime` field against the supported-runtime set. If the
runtime is NOT in the supported set, classify as **DEPRECATED_RUNTIME**.

**Currently supported runtimes (as of Aug 2026):**

| Language | Supported identifiers |
|---|---|
| Python | `python3.10`, `python3.11`, `python3.12`, `python3.13` |
| Node.js | `nodejs20.x`, `nodejs22.x` |
| Java | `java17`, `java21` |
| Go | `go1.x` (versionless — always tracks the latest Go release) |
| .NET | `dotnet8` |
| Ruby | `ruby3.2`, `ruby3.3` |
| Custom | `provided.al2023` |

**Deprecated (Phase 1 — create/update blocked, invocations still work):**

| Runtime | Deprecation context |
|---|---|
| `python3.9` | Python 3.9 upstream EOL Oct 2025; Lambda deprecation mid-2026 |
| `nodejs18.x` | Node 18 upstream EOL Apr 2025; Lambda deprecation late 2025 |
| `dotnet6` | .NET 6 upstream EOL Nov 2024; Lambda deprecation early 2026 |
| `ruby2.7` | Ruby 2.7 upstream EOL Mar 2023; Lambda deprecation completed |
| `provided.al2` | Amazon Linux 2 approaching EOL mid-2026 (flag as CONFIG_GAP, not DEPRECATED) |

**Blocked (Phase 2 — invocations fail with Runtime.UnsupportedException):**

| Runtime | Block context |
|---|---|
| `python3.8`, `python3.7`, `python3.6`, `python2.7` | All blocked |
| `nodejs16.x`, `nodejs14.x`, `nodejs12.x`, `nodejs10.x`, `nodejs8.10` | All blocked |
| `java8`, `java8.al2` | Blocked |
| `dotnet3` (Core 3.1), `dotnet2` (2.1) | Blocked |
| `ruby2.5` | Blocked |
| `provided` (Amazon Linux 1) | Blocked — AL1 fully EOL |

**If the runtime is deprecated or blocked**, emit DEPRECATED_RUNTIME with
the phase (Phase 1 = time bomb, Phase 2 = function already broken).

### Step 2: Function URL / public exposure evaluation

Check the `FunctionUrlConfig` (from `get-function-url-config`):

- **`AuthType: NONE`** → **PUBLIC_EXPOSURE**. The function is invocable by
  anyone on the internet via the Function URL. No IAM check, no signing,
  no authentication of any kind. The only controls are account-level
  concurrency/throttling limits.

- **`AuthType: AWS_IAM`** → No public-exposure finding from the URL itself.
  The caller must have `lambda:InvokeFunctionUrl` permission. This is the
  safe default.

- **No Function URL configured** → No public-exposure finding from URLs.
  Proceed to check the resource-based policy for cross-account
  `lambda:InvokeFunction` grants (see below).

**Resource-based policy cross-account check:** if the function's
resource-based policy (`get-policy`) grants `lambda:InvokeFunction` to a
`Principal: "*"` or a cross-account ARN without a `Condition`, this is a
secondary PUBLIC_EXPOSURE signal — weaker than a URL with NONE auth (the
caller still needs AWS credentials) but still a broad exposure. If a
Function URL with NONE auth is present, the URL finding takes precedence
and the resource-based policy finding is noted in FINDINGS but does not
change the verdict.

### Step 3: Execution role / IAM evaluation

Enumerate ALL policies attached to the execution role: managed (AWS and
customer, via `list-attached-role-policies`) AND inline (via
`list-role-policies`). Evaluate each Allow statement:

- **`Action: "*"` on `Resource: "*"`** → **OVERPERMISSIVE**.
  AdministratorAccess-equivalent. The function can perform any AWS API
  call in the account.

- **Privilege-escalation service wildcard on `"*"`** (`iam:*`, `sts:*`,
  `kms:*`, `secretsmanager:*`, `lambda:*`) → **OVERPERMISSIVE**. These
  enable privilege escalation by design.

- **Any service wildcard (`s3:*`, `dynamodb:*`, `ec2:*`) on
  `Resource: "*"`** → **OVERPERMISSIVE**. No scope restriction on either
  axis.

- **`iam:PassRole` on `"*"`** → **OVERPERMISSIVE**. The function can pass
  any role to any service — the single most common privesc vector.

- **`NotAction` / `NotResource` in an Allow** → **OVERPERMISSIVE**. Inverse
  wildcards grant everything except the listed values.

- **Named actions on specific ARNs** → OK for this dimension (least
  privilege).

- **Log-group-scoped CloudWatch Logs permissions** (`logs:CreateLogStream`,
  `logs:PutLogEvents` scoped to the function's log group) → NORMAL and
  required. Do NOT flag.

### Step 4: Observability / config-gap evaluation

Check the following configuration attributes. Any one produces
**CONFIG_GAP** (only if no higher-priority finding is present):

- **`TracingConfig.Mode: PassThrough`** → CONFIG_GAP. The function has no
  active X-Ray tracing. Most non-API-Gateway triggers produce zero traces.
  Only `Active` mode guarantees trace recording.

- **Missing `DeadLetterConfig`** on a function invoked asynchronously
  (EventBridge, S3, SNS, SQS) → CONFIG_GAP. Failed async invocations are
  retried twice then silently discarded. A DLQ (SQS or SNS) captures them
  for inspection. Functions invoked only synchronously (API Gateway,
  Function URL, SDK `Invoke`) do not need a DLQ — note this distinction.
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

- **CloudWatch Logs retention not set** → CONFIG_GAP. Lambda auto-creates
  a log group with `NeverExpire` retention. Logs accumulate indefinitely
  — a cost and compliance gap. Check retention with:
  `aws logs describe-log-groups --log-group-name-prefix /aws/lambda/<name>
  --query 'logGroups[*].retentionInDays' --profile <p>`
  A `null` or absent `retentionInDays` means NeverExpire. Set with:
  `aws logs put-retention-policy --log-group-name /aws/lambda/<name>
  --retention-in-days 30`

- **`ReservedConcurrentExecutions: 0`** → CONFIG_GAP. The function is
  effectively disabled — all invocations are throttled.

### Step 5: Aggregation — worst finding wins

The final verdict is the **maximum-severity** finding across all
dimensions, where:

```
DEPRECATED_RUNTIME > PUBLIC_EXPOSURE > OVERPERMISSIVE > CONFIG_GAP > OK
```

If no findings (all dimensions clean), the verdict is **OK**.

## Output format (per function)

```text
FUNCTION: <function-name>
VERDICT: DEPRECATED_RUNTIME | PUBLIC_EXPOSURE | OVERPERMISSIVE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [DEPRECATED_RUNTIME] <finding description (Step 1)>
  - [PUBLIC_EXPOSURE] <finding description (Step 2)>
  - [OVERPERMISSIVE] <finding description (Step 3)>
  - [CONFIG_GAP] <finding description (Step 4)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — deprecated runtime with public URL

```text
FUNCTION: nodejs16-public-and-deprecated
VERDICT: DEPRECATED_RUNTIME
REASON: Runtime nodejs16.x is in Phase 2 block — invocations are already
failing with Runtime.UnsupportedException (Step 1). A public Function URL
(AuthType NONE) is a secondary finding.
FINDINGS:
  - [DEPRECATED_RUNTIME] nodejs16.x is blocked (Phase 2) — function
    invocations fail. LastModified 2023-08-10 (>180 days stale).
  - [PUBLIC_EXPOSURE] Function URL AuthType NONE — publicly invocable.
    (Downgraded because the function is already non-functional.)
  - [OK] Execution role scoped to dynamodb:GetItem + Logs.
  - [OK] Tracing Active.
REMEDIATION:
  1. Update the runtime: aws lambda update-function-configuration
     --function-name nodejs16-public-and-deprecated --runtime nodejs20.x.
  2. If the public URL is required, change AuthType to AWS_IAM:
     aws lambda update-function-url-config --function-name ... --auth-type AWS_IAM.
```

## Edge-case handling

- **Container-image function (`PackageType: Image`).** The `Runtime`
  field is empty — skip Step 1. Note in FINDINGS: "Runtime check N/A for
  PackageType: Image — audit the container image for OS/runtime CVEs via
  ECR image scanning." Still audit Steps 2-4.

- **`provided.al2023` custom runtime.** Do NOT flag as deprecated. AWS
  does not manage the runtime version for custom runtimes — the operator
  does. Note in FINDINGS: "Custom runtime provided.al2023 — runtime
  version managed by operator, not deprecation-tracked by AWS."

- **Function with no resource-based policy.** `get-policy` returns
  `ResourceNotFoundException`. This is NORMAL — most functions do not have
  a resource-based policy. Do NOT flag the absence of a policy as an
  error or finding.

- **Layer-only runtime override.** A function on `python3.12` with a
  custom layer that bundles python3.9 binaries is still classified by the
  `Runtime` field (python3.12) — the layer content is invisible to the
  Lambda API. Note this limitation in FINDINGS if layers are present.

- **Multiple functions with the same role.** When auditing a fleet, the
  same execution role may be shared by many functions. An
  OVERPERMISSIVE role flags ALL functions using it. Note the shared role
  in FINDINGS to avoid re-scoping the same role N times.

## Anti-Patterns — NEVER

- NEVER classify a deprecated runtime as CONFIG_GAP or OVERPERMISSIVE.
  A deprecated runtime is a **scheduled outage** — AWS will disable the
  function on a known date. This is categorically different from "missing
  tracing" or "broad role." DEPRECATED_RUNTIME is the highest-priority
  verdict.

- NEVER flag `PackageType: Image` functions for "missing Runtime." The
  runtime is in the container image, not the Lambda metadata. The
  `Runtime` field is intentionally empty for container functions. Flagging
  this is a false positive.

- NEVER flag `provided.al2023` as deprecated. This is the current
  custom-runtime identifier. AWS does not track deprecation for
  `provided.*` identifiers. Only `provided` (AL1, fully EOL) is
  DEPRECATED_RUNTIME.

- NEVER treat a Function URL with `AuthType: AWS_IAM` as public
  exposure. AWS_IAM requires the caller to have `lambda:InvokeFunctionUrl`
  permission. It is the authenticated mode. Only `AuthType: NONE` is
  PUBLIC_EXPOSURE.

- NEVER classify `logs:CreateLogStream` and `logs:PutLogEvents` scoped to
  the function's own log group as over-permissive. These are **required**
  for Lambda execution — without them, the function cannot write logs.
  Every execution role needs these.

- NEVER recommend `AdministratorAccess` or any AWS-managed power-user
  policy as remediation. Replacing one over-permissive policy with another
  does not fix the finding. Always scope to named actions on specific ARNs.

- NEVER skip the execution-role audit because the runtime is deprecated.
  A function on python3.9 with `Action: "*"` has TWO findings
  (DEPRECATED_RUNTIME + OVERPERMISSIVE). Both appear in FINDINGS; the
  verdict is DEPRECATED_RUNTIME (worst).

- NEVER assume a function with no Function URL is not publicly exposed.
  Check the resource-based policy (`get-policy`) for cross-account
  `lambda:InvokeFunction` grants. A function can be publicly invocable
  via a resource-based policy even without a Function URL.

- NEVER leave a resource-based policy with `Principal: "*"` on
  `lambda:InvokeFunction` unflagged. This is an over-permissive
  resource-based policy — any AWS principal in any account can invoke
  the function. It is not the same as a Function URL with `AuthType:
  NONE` (which needs no AWS credentials at all), but it is still a
  broad exposure. Always emit a `[PUBLIC_EXPOSURE]` finding with the
  note "resource-based policy grants `lambda:InvokeFunction` to
  `Principal: *` — restrict to specific principals or add a `Condition`
  (e.g., `aws:SourceAccount`, `aws:SourceArn`)." If the policy also
  uses `Principal: "*"` with `Action: "*"` on the function, this is a
  critical misconfiguration — treat as Tier 3 exposure.

- NEVER flag a DLQ absence on a synchronous-only function. DLQs apply to
  async invocations (EventBridge, S3, SNS, SQS). A function invoked only
  via API Gateway or SDK `Invoke` is synchronous — there is no retry, so
  no DLQ is needed.

- NEVER treat `TracingConfig: Active` as sufficient observability on its
  own. Active tracing produces X-Ray segments, but CloudWatch Logs
  retention, DLQ, and alarms are independent. Flag each gap separately.

- NEVER recommend changing the runtime without testing the code first.
  A runtime upgrade (e.g., python3.9 → python3.12) may introduce breaking
  changes (stdlib removals, deprecation of language features). The
  remediation CLI is the target state; the operator must validate first.

- NEVER recommend downgrading an over-permissive role without checking
  for condition-key mitigations first. An execution role with `s3:*` on
  `"*"` but a `Condition: {"StringEquals": {"aws:SourceVpce":
  "vpce-xxx"}}` is already VPC-scoped — the blast radius is the VPC, not
  the entire internet. Note the condition in FINDINGS and recommend
  tightening only if the condition is absent or weak. A remediation that
  removes the condition alongside the wildcard creates a worse posture
  than the original.

- NEVER flag `AWSLambdaBasicExecutionRole` as over-permissive. This
  managed policy grants only CloudWatch Logs permissions (CreateLogGroup,
  CreateLogStream, PutLogEvents) — it is the minimum-safe policy for any
  Lambda function. Removing it breaks logging.

- NEVER recommend `PowerUserAccess`, `AmazonS3FullAccess`, or any broad
  AWS-managed power policy as a remediation for an over-permissive role.
  `PowerUserAccess` grants full access to every service except IAM —
  still effectively admin-level. `AmazonS3FullAccess` grants `s3:*` on
  `*`. These reintroduce the exact blast radius being constrained.
  Always scope to named actions on specific ARNs derived from CloudTrail
  or IAM Access Analyzer.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (update-function-configuration, update-function-url-config,
  put-function-concurrency, delete-function-url-config), the auditor
  MUST emit:
  `CONFIRM: About to <action> on function <name> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Before updating a runtime**, verify the code is compatible:
  (1) Check for deprecated stdlib modules removed in the target version.
  (2) Run the function locally or in a staging alias with the new runtime.
  (3) Update via a **published alias** (`--qualifier`) — never update
  `$LATEST` directly in production. Publish a new version, test, then
  shift traffic.

- **Before changing `AuthType` from NONE to AWS_IAM**, verify that all
  callers have `lambda:InvokeFunctionUrl` permission. Switching auth type
  breaks unauthenticated callers immediately — if the function URL is
  embedded in a web app or webhook, this is a breaking change.

- **Before scoping down an execution role**, capture the current policy
  for rollback:
  `aws iam get-role-policy --role-name <role> --policy-name <policy> > /tmp/<role>-backup-$(date +%s).json`
  Test the scoped policy in staging first. A too-narrow role produces
  `AccessDenied` at runtime — not at deploy time.

- Prefer **additive changes** (add a permissions boundary, add a Deny
  statement) over destructive changes (remove an Allow) — additive
  changes are reversible.

## Remediation guidance

### For DEPRECATED_RUNTIME — runtime upgrade

1. Identify the target runtime from the supported-runtime table. Choose
   the closest major version (python3.9 → python3.12, nodejs16.x →
   nodejs20.x).
2. Test code compatibility: run unit/integration tests against the target
   runtime. Check for removed stdlib modules and language-feature changes.
3. Update the function:
   `aws lambda update-function-configuration --function-name <name> --runtime <target> --profile <p>`
4. Publish a new version: `aws lambda publish-version --function-name <name>`
5. If using aliases, point the production alias at the new version after
   validation.
6. Monitor CloudWatch Logs for runtime errors for 24-48 hours.

### For PUBLIC_EXPOSURE — restrict function URL

1. If the URL was created by mistake, delete it:
   `aws lambda delete-function-url-config --function-name <name>`
2. If the URL is required, switch to authenticated mode:
   `aws lambda update-function-url-config --function-name <name> --auth-type AWS_IAM`
3. Grant callers `lambda:InvokeFunctionUrl` via IAM policy.
4. If public access is genuinely required (e.g., a webhook receiver), add
   a CloudFront distribution + WAF in front of the URL for rate-limiting
   and request validation. Do not expose the raw Function URL.

### For OVERPERMISSIVE — scope down execution role

1. Identify the actual AWS API calls the function makes (CloudTrail,
  90-day window of events for the role ARN).
2. Build a least-privilege policy from observed actions + resources.
3. Use AWS IAM Access Analyzer policy generation for automated scoping.
4. Create a new scoped managed policy and attach it to the role.
5. Remove the over-permissive policy after validation.
6. Verify with `aws iam simulate-principal-policy` against the new policy.

### For CONFIG_GAP — close observability gaps

1. **Enable active tracing:**
   `aws lambda update-function-configuration --function-name <name> --tracing-config Mode=Active`
2. **Add a DLQ (for async-invoked functions):**
   `aws lambda update-function-configuration --function-name <name> --dead-letter-config TargetArn=<sqs-or-sns-arn>`
3. **Set log retention:**
   `aws logs put-retention-policy --log-group-name /aws/lambda/<name> --retention-in-days 30`
4. **Remove reserved-concurrency kill switch** (if `0`):
   `aws lambda delete-function-concurrency --function-name <name>`

### For OK

1. No remediation required.
2. Recommend periodic re-audit when AWS publishes new runtime deprecation
   schedules (check the AWS Lambda runtime release notes quarterly).
3. Recommend enabling CloudWatch Alarms on `Errors`, `Throttles`, and
   `Duration` (p99) as proactive monitoring.

## Deep reference: Lambda runtime lifecycle internals

### Deprecation timeline mechanics

AWS publishes a runtime deprecation schedule on the Lambda programming
model release page. The timeline has two phases:

1. **Phase 1 — Deprecation (create/update block).** On the deprecation
   date, AWS blocks creation of new functions and updates to existing
   functions using the runtime. Existing functions **continue to
   execute** normally. This phase lasts ~30-60 days (the exact window
   varies by runtime). During this window, you can still update the
   runtime to a supported version — that is the only update allowed.

2. **Phase 2 — Block (invocation disable).** On the block date, AWS
   **disables** functions using the runtime. Invocations return
   `Runtime.UnsupportedException`. The function is non-functional.
   Event-source mappings (SQS, DynamoDB Streams, Kinesis) stop polling.
   Scheduled rules (EventBridge) invoke and fail silently.

The deprecation date is announced 6+ months in advance. The block date
is typically 30-60 days after the deprecation date. AWS sends email
notifications to account owners before each phase.

### Container-image function runtime tracking

For `PackageType: Image` functions, the Lambda API does not track the
runtime — it only tracks the ECR image URI. The runtime is determined by
the base image used in the Dockerfile (`public.ecr.aws/lambda/python:3.12`,
etc.). To audit runtime CVEs on container functions:

1. List the image URI from `get-function-configuration` → `Code` →
   `ImageUri`.
2. Enable ECR image scanning on the repository:
   `aws ecr put-image-scanning-configuration --repository-name <repo> --image-scanning-configuration scanOnPush=true`
3. Fetch the scan findings:
   `aws ecr describe-image-scan-findings --repository-name <repo> --image-id imageTag=<tag>`
4. Map the base image to the runtime version and check against the
   deprecation table.

### Function URL invocation mechanics

A Function URL with `AuthType: NONE` accepts any HTTP request. The
invocation does NOT pass through API Gateway, WAF, or any IAM check. The
URL format is `https://<url-id>.lambda-url.<region>.on.aws`. There is no
way to restrict access by IP, header, or token at the Lambda layer — the
only controls are:

- Account-level concurrency/throttling limits.
- Application-level validation inside the handler (checking headers,
  API keys, etc.).
- Placing a CloudFront distribution + WAF in front (recommended for any
  public-facing function).

Switching to `AuthType: AWS_IAM` requires the caller to sign requests
with SigV4 and have `lambda:InvokeFunctionUrl` permission. This is
incompatible with browser-based direct calls (browsers cannot sign SigV4
requests without a backend).

## Recent AWS features (2024-2026)

- **Lambda MicroVM / isolated sandboxes (2025-2026):** AWS introduced MicroVM support for Lambda, providing isolated sandboxes with full lifecycle control. Auditors should verify that functions requiring stronger isolation (e.g., multi-tenant SaaS) use the MicroVM isolation level — this is a new configuration field to audit.
- **SnapStart for Python and Ruby (2024-2025):** SnapStart (previously Java-only) now supports Python and Ruby runtimes. Auditors should verify that latency-sensitive Python/Ruby functions have SnapStart enabled, and that SnapStart initialization code does not cache stale credentials (a known SnapStart security consideration).
- **Response streaming (2024):** Lambda response streaming via Function URLs allows sending partial responses before completion. Auditors should note that streaming functions with `AuthType: NONE` expose a public streaming endpoint — the same PUBLIC_EXPOSURE classification applies.
- **New runtimes — python3.13, nodejs22.x (2024-2025):** The skill already tracks these in the supported-runtime table. Auditors should verify that new projects use the latest runtime and that deprecated runtimes are migrated on schedule.
- **Lambda Web Adapter (2024):** Lambda Web Adapter allows running web frameworks (FastAPI, Express, Spring Boot) on Lambda. No new audit-surface fields, but auditors should note that Web Adapter functions may expose additional HTTP endpoints via Function URLs.
- **Environment variable size increase (2024):** Lambda increased the total environment variable size limit from 4 KB to 8 KB. This does not change the audit logic but means auditors should be more vigilant about plaintext secrets in environment variables — the larger size makes it easier to embed secrets accidentally.

## Domain

AWS CloudOps / Lambda Compute Security & Runtime Compliance.
