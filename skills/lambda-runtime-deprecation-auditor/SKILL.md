---
name: lambda-runtime-deprecation-auditor
description: Audits AWS Lambda functions for deprecated/EOL runtimes (python3.9, nodejs16.x, etc.), over-permissioned execution roles (admin wildcards, privilege-escalation actions), public function URL exposure (AuthType NONE), and observability config gaps (missing X-Ray tracing, missing DLQ, log retention). Emits a deterministic verdict (DEPRECATED_RUNTIME | OVERPERMISSIVE | PUBLIC_EXPOSURE | CONFIG_GAP | OK) per function with enumerated findings and CLI remediation. Use when reviewing Lambda functions, checking runtime deprecation status, auditing execution-role scope, validating function-URL exposure, or hardening Lambda posture before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline config-document classification. Live-account audits use aws lambda get-function, get-function-url-config, get-policy, and list-functions (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  verdict_shape: DEPRECATED_RUNTIME | OVERPERMISSIVE | PUBLIC_EXPOSURE | CONFIG_GAP | OK
  when_to_use: Reviewing a Lambda function before production deployment, checking for deprecated or EOL runtimes, auditing an execution role for wildcard permissions, validating function-URL public exposure, or hardening observability configuration (tracing, DLQ, log retention) across a serverless fleet.
  activation_triggers: audit this Lambda function, is my Lambda runtime deprecated, check Lambda execution role, is my function URL public, Lambda AuthType NONE, missing X-Ray tracing Lambda, Lambda runtime EOL, hardening Lambda function, Lambda admin role
  invocation_schema: 'Input: either (a) a Lambda function configuration (Runtime, Handler, TracingConfig, DeadLetterConfig, Execution role + policies, Function URL config), OR (b) a function name/ARN for live-account audit. Output: deterministic FUNCTION/VERDICT/REASON/FINDINGS/REMEDIATION block per function, where VERDICT ∈ {DEPRECATED_RUNTIME, OVERPERMISSIVE, PUBLIC_EXPOSURE, CONFIG_GAP, OK}. ERROR is emitted only for malformed input and is not a classification verdict.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Lambda, runtime deprecation, EOL runtime, python3.9, nodejs16, deprecated runtime, execution role, over-permissive, AdministratorAccess, function URL, AuthType NONE, public exposure, X-Ray tracing, TracingConfig, PassThrough, Active tracing, dead letter queue, DLQ, Lambda audit, serverless security, runtime block, function hardening
  tags: lambda, security, runtime-deprecation, execution-role, function-url, tracing, audit, compute
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

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) — load on demand.


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


Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.


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

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

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

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.


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

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


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

Moved verbatim to [references/error-handling.md](references/error-handling.md) — load on demand.


## Deep reference: Lambda runtime lifecycle internals

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.



## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 expert behaviors, edge-case catalog, runtime lifecycle internals, recent AWS features
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — multi-function sweep / pagination commands, async-trigger detection sequence
- [references/error-handling.md](references/error-handling.md) — per-verdict remediation guidance with CLI
- [references/worked-examples.md](references/worked-examples.md) — formal input schema (live-account and offline-classification modes)

## Domain

AWS CloudOps / Lambda Compute Security & Runtime Compliance.

## AWS documentation

- **AWS Lambda Developer Guide** — https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
- **Lambda Security** — https://docs.aws.amazon.com/lambda/latest/dg/lambda-security.html
- **Lambda API Reference** — https://docs.aws.amazon.com/lambda/latest/APIReference/
- **AWS CLI Lambda Command Reference** — https://docs.aws.amazon.com/cli/latest/reference/lambda/
- **Lambda runtime deprecation policy** — https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
- **SnapStart** — https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html
