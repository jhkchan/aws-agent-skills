---
name: cloudwatch-synthetics-troubleshooter
description: Diagnoses CloudWatch Synthetics canary failures via a symptom-to-cause decision tree covering all five canary types (GUI Selenium WebDriver, HTTP ping, API HTTP, broken-link checker, multi-step), runtime exceptions (Node.js and Python), canary timeout (exceeded max duration), Visual Monitoring screenshot comparison baseline mismatch, authentication failures (canary cannot log in), and blue/green deployment artifact mismatches. Walks canary run logs, HAR files, step-level screenshots, CloudWatch metrics (SuccessPercent, Duration), and canary artifact locations to pinpoint the failure type. Emits a deterministic verdict (ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE) with the specific failure category, evidence from the run report, and a concrete fix. Use when a Synthetics canary transitions to FAILED state, SuccessPercent drops below threshold, Visual Monitoring reports a baseline mismatch, or the canary logs show timeout, auth, or runtime exceptions.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works from pasted canary run reports, error strings, and CloudWatch metric observations. Live-account diagnosis uses aws synthetics describe-canaries, describe-canary-runs, get-canary-runs, aws logs start-query, aws s3 ls on the artifact bucket, and aws cloudwatch get-metric-statistics for CloudWatchSynthetics metrics (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: cloudwatch, synthetics, canary, management, troubleshoot, visual-monitoring, selenium
  dependencies: aws-orchestrator
  keywords: CloudWatch Synthetics, canary, GUI Selenium, WebDriver, HTTP canary, API canary, broken-link checker, multi-step canary, Visual Monitoring, screenshot comparison, baseline mismatch, canary timeout, Node.js runtime, Python runtime, authentication failure, blue/green deployment, canary recording, SuccessPercent, troubleshooting
  when_to_use: Diagnosing a CloudWatch Synthetics canary that has transitioned to FAILED state, SuccessPercent below threshold, Visual Monitoring baseline mismatch alerts, canary timeout errors, authentication failures where the canary cannot log in, runtime exceptions in Node.js or Python canary scripts, broken-link checker failures, or blue/green deployment artifact mismatches.
  when_not_to_use: Canary provisioning or script authoring, CloudWatch alarm configuration audits (use cloudwatch-alarm-auditor), IAM policy authoring for the canary execution role. This skill diagnoses canary failures; it does not author canary scripts.
  activation_triggers: CloudWatch Synthetics canary FAILED, Synthetics canary failure, canary SuccessPercent low, Synthetics Visual Monitoring mismatch, canary screenshot comparison failure, canary timeout exceeded max duration, Synthetics canary authentication failure, canary cannot log in, Synthetics canary runtime exception, troubleshoot CloudWatch canary
  invocation_schema: 'Input: either (a) a symptom description (canary name, failure state, observed CloudWatch metric pattern, error string from the run report), optionally paired with describe-canary output, OR (b) a canary name plus caller context for live-account diagnosis. Output: a deterministic CANARY / VERDICT / ROOT_CAUSE / FAILURE_TYPE / EVIDENCE / REMEDIATION block where VERDICT is one of {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and FAILURE_TYPE is one of {TIMEOUT, AUTH_FAILURE, VISUAL_MONITORING_MISMATCH, RUNTIME_EXCEPTION, TARGET_ENDPOINT_DOWN, NETWORK_ERROR, DNS_FAILURE, ARTIFACT_MISMATCH, RATE_LIMITED, SCRIPT_BUG, INSUFFICIENT_PERMISSIONS, UNKNOWN}.'
---

# CloudWatch Synthetics Troubleshooter

## What this skill does

Diagnoses CloudWatch Synthetics canary failures via a symptom-to-cause
decision tree spanning all five canary types, runtime exceptions, Visual
Monitoring baseline mismatches, authentication failures, timeouts, and
blue/green deployment artifact issues. Emits a deterministic verdict
with the specific failure type, evidence, and a concrete fix.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Symptom-to-failure-type lookup table | Start here for fast triage |
| **STRICT output contract** | Mandatory output block format | Before emitting any response |
| **Mindset** | Canary-vs-target distinction, the five canary types | Understanding the diagnostic model |
| **Expert heuristic** | Non-obvious canary failure behaviours | Review before complex diagnosis |
| **Process** | Ordered diagnostic walk (Steps 0-9) | When running the full diagnosis |
| **NEVER** | Top 5 anti-patterns that cause misdiagnosis | Review before risky recommendations |
| **Recent AWS features** | 2024-2026 Synthetics updates | Reference for latest capabilities |

## Quick reference — symptom to failure type

| Observed signal | Failure type | First probe |
|---|---|---|
| Run FAILED, Duration at/near `TimeoutInSeconds` | TIMEOUT | Check timeout vs run Duration; last step in log |
| Error contains 401/403, "Unauthorized", "Login failed" | AUTH_FAILURE | Check Secrets Manager rotation, token expiry |
| `VisualMonitoringBaselineMismatch` | VISUAL_MONITORING_MISMATCH | Compare screenshot to baseline; check UI deploy |
| `SyntaxError`, `TypeError`, `ReferenceError`, `Exception` | RUNTIME_EXCEPTION | Inspect canary script stack trace |
| All requests return non-200, target unreachable | TARGET_ENDPOINT_DOWN | Verify target independently; Route 53 health |
| DNS resolution failure | DNS_FAILURE | VPC DNS settings, Route 53, security groups |
| Artifact zip hash differs post-deployment | ARTIFACT_MISMATCH | Compare SHA; check blue/green bucket/IAM |
| 429 from target API | RATE_LIMITED | Canary frequency vs target API rate limits |
| `AccessDenied`, `NoSuchBucket`, `PermissionDenied` | INSUFFICIENT_PERMISSIONS | Canary execution role IAM and bucket policy |

## STRICT output contract

Every diagnosis response MUST emit this block. No prose before the
block; the block is the entire actionable output.

```text
CANARY: <canary name> in <region>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <failure type name> — <specific root cause>
FAILURE_TYPE: <TIMEOUT | AUTH_FAILURE | VISUAL_MONITORING_MISMATCH |
               RUNTIME_EXCEPTION | TARGET_ENDPOINT_DOWN | NETWORK_ERROR |
               DNS_FAILURE | ARTIFACT_MISMATCH | RATE_LIMITED |
               SCRIPT_BUG | INSUFFICIENT_PERMISSIONS | UNKNOWN>
EVIDENCE:
  - <run report signal>: <error string or status>
  - <CloudWatch metric signal>: <metric and value>
  - <canary config signal>: <field and value>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific fix with CLI command>
  2. <verification command>
  3. <post-apply monitoring>
```

Do NOT omit any field. If a field is not applicable, write `N/A` with a
one-line reason.

## Mindset

**One-line takeaway:** A canary failure does not always mean "the target
is down." Synthetics canaries fail for eleven distinct reasons, and the
FAILED state alone is insufficient to distinguish them. The diagnostic
walk combines the run report error, the canary type, the target endpoint
status, Visual Monitoring baseline state, and CloudWatch metrics.

Three-facts deep-dive (canary-side problems, Visual Monitoring vs functional failures, over-diagnosed timeout): [Advanced patterns](references/advanced-patterns.md).

## Expert heuristic — non-obvious canary failure behaviours

All nine non-obvious behaviours (shared execution role, baseline auto-update, VPC routing, run-frequency overlap, describe-canary limits, blue/green artifacts, unhandled promise rejections, third-party links, canary recording): [Advanced patterns](references/advanced-patterns.md).

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the failure signal

Gather these four pieces before proceeding.

| Signal | Source | Why required |
|---|---|---|
| **Canary name + region** | User-provided or `describe-canaries` | All API and log calls need this |
| **Run report error** | `get-canary-runs --name <canary>` | Drives the symptom category |
| **Canary type + runtime + timeout** | `describe-canary --name <canary>` | Determines which diagnostic path applies |
| **CloudWatch metric pattern** | `get-metric-statistics` on `CloudWatchSynthetics` | Confirms sustained vs transient failure |

If the canary name or region is unknown, emit NEED_MORE_INFO:

```text
CANARY: <canary name or unknown>
VERDICT: NEED_MORE_INFO
ROOT_CAUSE: UNKNOWN — cannot diagnose without the canary name and region
FAILURE_TYPE: UNKNOWN
EVIDENCE:
  - Run report: not available (canary name not provided)
ROOT_CAUSE_CATALOG: #0
REASON: Identify the failing canary from the CloudWatch alarm, the
  Synthetics console (filter State: FAILED), or
  aws synthetics describe-canaries --query 'Canaries[?State==`ERROR`]'
MISSING:
  - Canary name + region
  - The run report error string
  - The canary type (GUI Selenium, HTTP, API, broken-link, multi-step)
```

### Step 1: Identify the symptom category

| Category | Signature | Diagnostic step |
|---|---|---|
| **A. TIMEOUT** | FAILED, Duration >= `TimeoutInSeconds`, no specific error | Step 2 |
| **B. AUTH_FAILURE** | Error contains 401, 403, "Unauthorized", "Login failed" | Step 3 |
| **C. VISUAL_MONITORING_MISMATCH** | `VisualMonitoringBaselineMismatch` or screenshot delta | Step 4 |
| **D. RUNTIME_EXCEPTION** | `SyntaxError`, `TypeError`, `ReferenceError`, `Exception` | Step 5 |
| **E. TARGET_ENDPOINT_DOWN** | All requests non-200, target independently unreachable | Step 6 |
| **F. ARTIFACT/PERMISSIONS** | `AccessDenied`, `NoSuchBucket`, artifact hash mismatch | Step 7 |
| **G. NETWORK/DNS/RATE** | 429, `ECONNREFUSED`, `ENOTFOUND`, `ETIMEDOUT` | Step 8 |

Priority: AUTH_FAILURE precedes TARGET_ENDPOINT_DOWN precedes TIMEOUT
precedes VISUAL_MONITORING_MISMATCH precedes RUNTIME_EXCEPTION.

### Step 2: TIMEOUT diagnostic

Canary exceeded `TimeoutInSeconds` (default 60s, max 300s). The key
question: is the slowness target-side, script-side, or network-side?

**Canary timeout baselines:**

| Canary type | Typical Duration | Default timeout | Common slow-step |
|---|---|---|---|
| GUI Selenium | 15-30s | 60s | Page load, element wait |
| HTTP ping | 2-5s | 20s | DNS, connection |
| API HTTP | 5-15s | 30s | OAuth token, API response |
| Broken-link checker | 10-60s | 120s | Third-party link response |
| Multi-step | 20-90s | 120s | Step 2+ after login |

Probes (canary config with timeout, last 5 runs with duration, Duration metric trend): [Diagnostic commands](references/diagnostic-commands.md).

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Duration near timeout consistently, no single slow step | Target slow or script inefficient | Check target response time independently |
| Duration jumps after deployment | Target change increased latency | Correlate with deploy time; check APM |
| Duration spikes intermittently | Network path instability (NAT, TGW) | Check NAT gateway metrics, route tables |
| Duration near timeout, last step never logs | Script waits for removed selector | Inspect canary log for last logged step |

**Fix patterns:** Target slow (investigate target app), stale selector
(update canary script DOM selectors), VPC network (check NAT gateway
`ErrorPortAllocation`), run frequency too high (reduce from 1 min to
5 min).

### Step 3: AUTH_FAILURE diagnostic

Canary cannot authenticate. Common in GUI Selenium and API canaries
testing authenticated endpoints.

1. **Secrets Manager:** if canary reads credentials from Secrets
   Manager, verify the secret was not rotated. Canary role needs
   `secretsmanager:GetSecretValue`.
2. **Token expiry:** API canaries using OAuth/JWT may cache a token
   that expired. Script must refresh on each run.
3. **Credential validity:** test account may be locked, password
   changed, or MFA policy changed.
4. **Auth service:** Cognito, Auth0, or internal IdP may be down.

Probes (canary-log auth-error query, Secrets Manager rotation history, canary-role secret-access simulation): [Diagnostic commands](references/diagnostic-commands.md).

| Sub-symptom | Root cause | Fix |
|---|---|---|
| 401/403 on all requests | Credential expired or rotated | Update secret; verify rotation Lambda |
| "JWT expired" | Token cached beyond expiry | Modify script to fetch fresh token per run |
| "Login failed" (GUI) | Account locked/changed/MFA challenge | Reset test account; verify MFA policy |
| Auth service timeout | Auth provider down | Escalate to auth service team |

### Step 4: VISUAL_MONITORING_MISMATCH diagnostic

Step screenshot differs from baseline beyond tolerance. Separate from
functional errors — the canary's actions succeeded but the visual
comparison flagged a delta.

1. **Check for recent deployment:** if UI deployed, baseline is stale
   and needs updating, not the application.
2. **Download screenshot and baseline:** compare visually. Look for
   dynamic content (banners, popups, clocks, personalized content).
3. **Check tolerance setting:** `VisualTesting.Tolerance` (percentage).
4. **Check capture timing:** anti-flicker or loading-state may cause
   inconsistent screenshots.

Probes (Visual Monitoring config, failed-run artifact listing, screenshot download): [Diagnostic commands](references/diagnostic-commands.md).

| Sub-symptom | Root cause | Fix |
|---|---|---|
| Mismatch after known UI deploy | Baseline is stale | Update baseline via console or `update-canary` |
| Mismatch on one step, others pass | Dynamic content on that step | Add ignore region or increase tolerance |
| Mismatch intermittently | Anti-flicker or loading-state timing | Add explicit `await` for page-load-complete |
| Large delta on all steps | Real UI break or wrong page loaded | Check target URL; escalate to app team |

### Step 5: RUNTIME_EXCEPTION diagnostic

Canary script threw an unhandled exception. The run report contains a
stack trace or error string from the Node.js or Python runtime.

| Runtime | Exception | Common cause |
|---|---|---|
| Node.js | `TypeError: Cannot read properties of undefined` | DOM selector returned null |
| Node.js | `UnhandledPromiseRejectionWarning` | Missing `.catch()` or un-awaited async |
| Node.js | `ReferenceError: <var> is not defined` | Missing import or scope issue |
| Python | `NoSuchElementException` (Selenium) | Web element removed; DOM changed |
| Python | `TimeoutException` (WebDriverWait) | Element did not appear within wait |
| Python | `ImportError: No module named` | Missing dependency in artifact zip |

Probes (canary-log error/stack-trace query, runtime version, available runtime versions): [Diagnostic commands](references/diagnostic-commands.md).

**Fix patterns:** DOM change (update selectors, correlate with
deployment), unhandled promise (add `.catch()`, `await` all async calls),
missing dependency (rebuild zip with all modules), runtime upgrade
regression (pin version or update script).

### Step 6: TARGET_ENDPOINT_DOWN diagnostic

Target is genuinely unreachable or returning errors.

1. **Verify independently** from a different vantage point (curl,
   browser, another canary).
2. **Check Route 53 / DNS** health checks and failover records.
3. **Check ALB / CloudFront** target health and distribution status.
4. **Check AWS Health Dashboard** for regional degradation.

Probes (independent curl check, Route 53 test-dns-answer, ALB target health, SuccessPercent trend): [Diagnostic commands](references/diagnostic-commands.md).

**Fix patterns:** Application failure (escalate to app team), DNS
failure (fix Route 53 record/health check), network path (fix VPC
routing/NAT/SG), regional outage (AWS-side incident, escalate through
support).

### Step 7: ARTIFACT_MISMATCH / INSUFFICIENT_PERMISSIONS diagnostic

Canary cannot access its artifact bucket, execution role, or
dependencies. Canary-side configuration failure.

Probes (execution role and artifact location, IAM permission simulation, artifact zip existence): [Diagnostic commands](references/diagnostic-commands.md).

| Sub-symptom | Root cause | Fix |
|---|---|---|
| `AccessDenied` on S3 | Role lacks `s3:GetObject` | Add IAM permission to canary role |
| `NoSuchBucket` or `NoSuchKey` | Artifact bucket or zip deleted | Redeploy canary with correct artifact |
| `Module not found` post-deploy | Blue/green artifact mismatch | Compare hash; redeploy from correct source |
| `KMS AccessDenied` | Role lacks `kms:Decrypt` on CMK | Add `kms:Decrypt` to role policy |

### Step 8: RATE_LIMITED / NETWORK_ERROR / DNS_FAILURE diagnostic

Network-level failures distinct from target endpoint failures. The
target may be healthy but the canary's network path is blocked.

Probes (canary-log network-error query, VPC config): [Diagnostic commands](references/diagnostic-commands.md).

| Sub-symptom | Root cause | Fix |
|---|---|---|
| `429` from target API | Canary frequency exceeds API rate limit | Reduce run frequency; or exempt canary |
| `ECONNREFUSED` | Target port closed or firewall blocking | Check security groups, service status |
| `ENOTFOUND` (DNS) | VPC DNS failure or Route 53 record deleted | Check VPC DHCP options, Route 53 |
| `ETIMEDOUT` (network) | NAT, NACL, route table, or peering issue | Check NAT gateway, route tables, NACLs |

### Step 9: Map to root-cause catalog and decide verdict

| # | Root cause | Category |
|---|---|---|
| 1 | Timeout from slow target | TIMEOUT |
| 2 | Timeout from stale selector | TIMEOUT |
| 3 | Credential expired or rotated | AUTH_FAILURE |
| 4 | Visual Monitoring baseline stale after UI deploy | VISUAL_MONITORING_MISMATCH |
| 5 | Runtime exception from DOM change | RUNTIME_EXCEPTION |
| 6 | Runtime exception from unhandled promise | RUNTIME_EXCEPTION |
| 7 | Target endpoint genuinely down | TARGET_ENDPOINT_DOWN |
| 8 | Canaries role missing IAM permission | INSUFFICIENT_PERMISSIONS |
| 9 | Artifact zip missing or blue/green mismatch | ARTIFACT_MISMATCH |
| 10 | VPC canary DNS or network path failure | DNS_FAILURE / NETWORK_ERROR |
| 11 | Target API rate-limiting the canary | RATE_LIMITED |

**Verdict decision:**
- **ROOT_CAUSE_FOUND** — specific failure type identified with a
  specific cause (credential, selector, IAM policy, baseline, target).
- **NEED_MORE_INFO** — operator cannot supply evidence (canary name
  unknown, run report unavailable).
- **ESCALATE** — cause outside operator's scope: production outage,
  AWS regional degradation, or canary script bug requiring developer
  involvement.

## Output format

See STRICT output contract above. Worked examples below.

### Worked example — Visual Monitoring mismatch after UI deploy

```text
CANARY: checkout-ui-canary in us-east-1
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: VISUAL_MONITORING_MISMATCH — the checkout page was
  redesigned and deployed at 2026-08-09T14:00Z. The Visual Monitoring
  baseline was not updated. Step 3 (payment page) shows a 12.4% pixel
  delta vs the 1% tolerance: "Pay Now" button moved from right-aligned
  to center, and a new trust badge appears below the total.
FAILURE_TYPE: VISUAL_MONITORING_MISMATCH
EVIDENCE:
  - Run report: VisualMonitoringBaselineMismatch on step 3, delta 12.4%
  - CloudWatch SuccessPercent: dropped 100% to 0% at 2026-08-09T14:02Z
  - CloudWatch Duration: 18s (normal) — canary functionally succeeded
  - Deployment correlation: checkout-ui deployed at 2026-08-09T14:00Z
ROOT_CAUSE_CATALOG: #4
REMEDIATION:
  1. Confirm the UI change is intentional with the frontend team.
  2. Update the Visual Monitoring baseline via console or trigger:
      aws synthetics start-canary --name checkout-ui-canary
     Then update baseline from the new run's screenshots.
  3. Optionally increase tolerance to 2% for minor CSS shifts.
  4. Monitor SuccessPercent for 10 minutes; expect return to 100%.
```

Worked example — auth failure from secret rotation (ROOT_CAUSE_FOUND, catalog #3): [Worked examples](references/worked-examples.md).

Worked example — insufficient context (NEED_MORE_INFO): [Worked examples](references/worked-examples.md).

## Anti-Patterns — NEVER (top 5)

- **NEVER assume FAILED means "the target endpoint is down."** Eleven
  distinct root causes produce FAILED. Only one
  (TARGET_ENDPOINT_DOWN) is a genuine target outage. Auth failures,
  Visual Monitoring mismatches, runtime exceptions, IAM issues, and
  network problems all produce FAILED. Always read the run report.

- **NEVER raise `TimeoutInSeconds` as the first fix for a timeout.**
  The timeout is a symptom. The canary is slow because the target is
  slow, the script waits for a missing element, VPC networking is
  constrained, or run frequency causes overlap. Always identify the
  slow step first.

- **NEVER treat a Visual Monitoring mismatch as a production incident
  without checking for a recent deployment.** After a confirmed UI
  deployment, Visual Monitoring mismatch is EXPECTED — the baseline is
  stale. Update the baseline first; only escalate if no deployment
  occurred and the delta shows a broken layout.

- **NEVER diagnose canary failures without reading the run report.**
  `describe-canary` shows configuration and last run state, but NOT the
  error details. Always use `get-canary-runs` or `describe-canary-runs`
  to retrieve the actual error message and step results.

- **NEVER blame the canary script without checking the target
  independently.** A canary VPC networking issue, NAT gateway failure,
  or DNS misconfiguration can make a healthy target appear "down" to
  the canary while being reachable everywhere else. Verify the target
  from a different vantage point first.

## Remediation guidance

Per-failure-type remediation sequences (TIMEOUT, AUTH_FAILURE, VISUAL_MONITORING_MISMATCH, RUNTIME_EXCEPTION, TARGET_ENDPOINT_DOWN): [Error handling](references/error-handling.md).

## Diagnostic command reference

The eight numbered reference commands (list canaries, canary config, recent runs, SuccessPercent, log query, artifacts, manual run, IAM simulation): [Diagnostic commands](references/diagnostic-commands.md).

## Recent AWS features (2024-2026)

2024-2026 feature notes (canary recording, Visual Monitoring enhancements, Python runtime GA, VPC canary improvements, runtime lifecycle, blue/green deployments): [Advanced patterns](references/advanced-patterns.md).

## References

See `references/canary-type-reference.md` for full canary type
specifications (script templates, default timeout, common failure modes
per type), and `references/visual-monitoring-guide.md` for Visual
Monitoring configuration, tolerance tuning, and baseline management.

## References (load on demand)

- [Diagnostic commands](references/diagnostic-commands.md) — per-step probe commands (Steps 2-8) and the eight numbered reference commands
- [Error handling](references/error-handling.md) — remediation guidance by failure type
- [Worked examples](references/worked-examples.md) — auth-failure and insufficient-context worked examples
- [Advanced patterns](references/advanced-patterns.md) — mindset facts, expert heuristics, recent AWS features

## Domain

AWS CloudOps / CloudWatch Synthetics Canary Reliability and Visual
Monitoring.

## AWS documentation

- **CloudWatch Synthetics User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html
- **Canary types** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html#canary-types
- **Visual Monitoring** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/synthetics-visual-monitoring.html
- **Synthetics API Reference** — https://docs.aws.amazon.com/synthetics/latest/APIReference/
- **Synthetics CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/synthetics/
