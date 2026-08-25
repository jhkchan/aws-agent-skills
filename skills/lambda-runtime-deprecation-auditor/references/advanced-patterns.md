# Advanced Patterns — Lambda Runtime Deprecation Auditor

Deep-dive material moved verbatim from SKILL.md: Step-0 expert
knowledge, edge-case handling, runtime lifecycle internals, and recent
AWS features. Load on demand.

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

### Edge-case handling


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

### Deep reference: Lambda runtime lifecycle internals


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

### Recent AWS features (2024-2026)


- **Lambda MicroVM / isolated sandboxes (2025-2026):** AWS introduced MicroVM support for Lambda, providing isolated sandboxes with full lifecycle control. Auditors should verify that functions requiring stronger isolation (e.g., multi-tenant SaaS) use the MicroVM isolation level — this is a new configuration field to audit.
- **SnapStart for Python and Ruby (2024-2025):** SnapStart (previously Java-only) now supports Python and Ruby runtimes. Auditors should verify that latency-sensitive Python/Ruby functions have SnapStart enabled, and that SnapStart initialization code does not cache stale credentials (a known SnapStart security consideration).
- **Response streaming (2024):** Lambda response streaming via Function URLs allows sending partial responses before completion. Auditors should note that streaming functions with `AuthType: NONE` expose a public streaming endpoint — the same PUBLIC_EXPOSURE classification applies.
- **New runtimes — python3.13, nodejs22.x (2024-2025):** The skill already tracks these in the supported-runtime table. Auditors should verify that new projects use the latest runtime and that deprecated runtimes are migrated on schedule.
- **Lambda Web Adapter (2024):** Lambda Web Adapter allows running web frameworks (FastAPI, Express, Spring Boot) on Lambda. No new audit-surface fields, but auditors should note that Web Adapter functions may expose additional HTTP endpoints via Function URLs.
- **Environment variable size increase (2024):** Lambda increased the total environment variable size limit from 4 KB to 8 KB. This does not change the audit logic but means auditors should be more vigilant about plaintext secrets in environment variables — the larger size makes it easier to embed secrets accidentally.
