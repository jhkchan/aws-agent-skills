---
name: inspector2-finding-troubleshooter
description: Diagnoses Amazon Inspector v2 vulnerability findings through a finding-type-driven diagnostic tree covering network reachability (unreachable ports, unintended IGW exposure, SG/NAU cascade), package vulnerability (CVE in OS packages, language ecosystems npm/pip/gem/go, Lambda layers, ECR container images), and code vulnerability (Lambda code scanning for injection, hardcoded secrets, path traversal). Walks severity (Critical/High/Medium/Low) to remediation per type (patch packages via SSM Patch Manager, fix code, restrict security groups, rebuild ECR images, update Lambda layers), integrates SBOM export, Lambda layer scanning, ECR image scanning, and the latest Inspector code scanning for Lambda and SBOM export features. Emits ROOT_CAUSE_FOUND with the specific finding type, vulnerable artifact, and remediation path. Use when an Inspector finding fires, a CVE is reported on EC2/ECR/Lambda, network reachability is flagged, SBOM export shows vulnerable packages, or Lambda code scanning reports a code vuln.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline finding classification works from pasted finding JSON and CVE metadata. Live-account diagnosis uses aws inspector2 list-findings, describe-findings, batch-get-finding-details, list-coverage, list-sbom-export, batch-get-code-snippets, aws ecr describe-images and describe-image-scan-findings, aws lambda get-function-configuration, aws ssm list-inventory-entries, aws ec2 describe-security-groups, and aws...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, inspector, inspector2, vulnerability, cve, sbom, ecr-scan, lambda-scan, security, troubleshoot
  dependencies: aws-orchestrator
  keywords: aws, inspector, inspector v2, inspector2, vulnerability, CVE, network reachability, package vulnerability, code vulnerability, SBOM, software bill of materials, Lambda layer scanning, ECR image scanning, Lambda code scanning, patch management, SSM Patch Manager, security groups, SCA, SAST, cloudops, troubleshoot, security
  when_to_use: Diagnosing an Amazon Inspector v2 finding — a CVE on an EC2 instance, ECR image, or Lambda function; a network reachability finding flagging an unintended internet-exposed port; a package vulnerability in an OS package, language ecosystem (npm, pip, gem, go, maven), or Lambda layer; a code vulnerability from Inspector code scanning for Lambda (injection, hardcoded secrets, path traversal); an SBOM export showing vulnerable packages; triaging a Critical or High finding; deciding whether to patch, suppress, or restrict; or running a "what does this Inspector finding mean and how do I fix it" page where the root cause may be a stale package, an unintended SG rule, a Lambda layer rebuild, or a code fix — not necessarily the resource itself.
  when_not_to_use: Configuration posture audits (use securityhub-finding-auditor for control findings, AWS Config rule violations), Amazon Macie data classification alerts, Amazon GuardDuty threat detections (runtime threats — use guardduty-finding-troubleshooter), or AWS WAF blocks (use alb-5xx-troubleshooter step 5). This skill diagnoses Inspector scan findings (vulnerability + reachability + code), not detection services.
---

# Inspector v2 Finding Troubleshooter

An AWS CloudOps agent skill that diagnoses Amazon Inspector v2 findings
through a finding-type-driven decision tree. The skill walks each finding
to its root cause — vulnerable package, exposed port, Lambda code defect,
stale Lambda layer — with verify commands, emits remediation per type
(patch via SSM, restrict SGs, rebuild ECR images, update Lambda layers,
fix code), and surfaces SBOM export, Lambda layer scanning, ECR image
scanning, and the latest Inspector code scanning for Lambda features.

## What this skill does

Classifies an Inspector v2 finding by type (network reachability, package
vulnerability, code vulnerability), severity (Critical/High/Medium/Low),
resource (EC2, ECR, Lambda, ECR repository), walks a type-specific
diagnostic tree to the vulnerable artifact, emits a ROOT_CAUSE_FOUND
verdict with the specific finding type, the vulnerable package / CVE /
port / code location, and the remediation path. Validates SBOM export,
Lambda layer scanning, and Inspector code scanning outputs.

## STRICT output contract

When this skill is invoked with an Inspector finding (finding ARN,
finding JSON, CVE id, or a resource ARN flagged by Inspector), the agent
MUST respond with the diagnostic block defined in §"Output format" using
the literal all-caps labels `TARGET:`, `VERDICT:`, `REASON:`, `FINDING_TYPE:`,
`SEVERITY:`, `EVIDENCE:`, `REMEDIATION:`, and `CONFIRM:`. Do NOT preface
the block with prose, headings, or disclaimers — emit the block as the
first lines of the response. This contract is what assertion-based evals
and downstream remediation pipelines rely on; deviating from the literal
labels breaks automation silently.

## Mindset

**One-line takeaway:** an Inspector finding is a *symptom*, not a *root
cause*. The CVE names the vulnerability; the root cause is *why the
vulnerable artifact is present* — an unpatched package, an unintended
security group, a stale Lambda layer, an inherited base image. Treat the
finding as the entry point, not the conclusion.

- **Finding type drives the diagnostic.** Reachability → SG/NAU/IGW.
  Package → package managers (yum, apt, npm, pip, gem, go), SBOM,
  base image. Code → SAST rule, source line. Wrong type → wasted cycle.

- **Severity drives the SLA, not the root cause.** A Critical finding
  gets the page; the walk is identical. Do NOT skip evidence because
  the severity is Critical — false-positive Criticals are common (the
  vulnerable code path may be unreachable). Always verify with a probe.

- **The resource is not always the right place to fix.** A Lambda CVE
  is fixed at the *layer* or *deployment package*, not the function.
  An ECR CVE is fixed by *rebuilding the image*, not patching the
  running container. The skill routes the fix to the right layer.

## Philosophy

- **The finding JSON carries the root-cause signal.** The `Type`,
  `Title`, `Resources`, `PackageVulnerability` (CVE, package, version,
  fixed-in), `NetworkReachability` (port, protocol, CIDR), or
  `CodeVulnerability` (file, line, snippet) block is the primary
  diagnostic surface. Operators who "see the CVE but don't know what to
  do" have often not read the full JSON — `batch-get-finding-details`
  first.

- **Inspector scans at scan time, not real-time.** A finding may be
  stale: the package was already patched, the SG already restricted,
  the Lambda layer already updated. Verify against current state before
  recommending remediation. A finding `lastObservedAt` > 24h may
  already be fixed.

- **Reachability findings are topology problems, not package problems.**
  The fix is in the SG/NAU/IGW chain — restrict the SG, remove a public
  IP, add a NAT gateway, or isolate. Patching the resource's software
  does NOT close a reachability finding.

- **Lambda code scanning findings need code fixes, not package updates.**
  Inspector code scanning for Lambda (2024-2025) flags source defects
  (injection, hardcoded secrets, path traversal, weak crypto). The fix
  is in the application code. The skill reads the `CodeSnippet` from
  `batch-get-code-snippets` to pinpoint the line.

## Quick navigation

| If the symptom is... | Go to | First probe |
|---|---|---|
| `PackageVulnerability` finding on EC2 | Step 2a | `list-inventory-entries` for the CVE'd package |
| `PackageVulnerability` finding on ECR | Step 2b | `describe-image-scan-findings` for the image |
| `PackageVulnerability` finding on Lambda | Step 2c | `get-function-configuration` for layers + runtime |
| `NetworkReachability` finding on EC2 | Step 3a | `describe-security-groups` for the flagged port |
| `NetworkReachability` with IGW path | Step 3b | `describe-route-tables` + `describe-network-interfaces` |
| `CodeVulnerability` finding on Lambda | Step 4 | `batch-get-code-snippets` for the source line |
| Critical CVE without fixed-in version | Step 2d | upstream CVE database, vendor advisory |
| SBOM export shows vulnerable package | Step 5 | `list-sbom-export` + parse CycloneDX/SPDX |
| Finding `lastObservedAt` > 24h ago | Step 6 | rescan or check current state |
| Need the finding JSON format and fields | Reference | `references/finding-types-reference.md` |

## Pre-flight: finding classification and gather-info gate

Before running type-specific probes, gather the canonical finding JSON,
the resource metadata, and the Inspector coverage status. Misclassifying
the finding type (package vs reachability vs code) produces false root
causes and wrong remediation.

### Account-wide pre-flight commands

All pre-flight commands (read-only): see `references/diagnostic-commands.md` § Pre-flight.

### Finding-type short-circuit

| `Type` field | Effect on diagnosis |
|---|---|
| `PACKAGE_VULNERABILITY` | **Package CVE.** Look at `PackageVulnerability` block: CVE id, package name, vulnerable range, fixed-in version. Resource type (EC2, ECR, Lambda) determines the patch surface. |
| `NETWORK_REACHABILITY` | **Reachability.** Look at `NetworkReachability` block: port, protocol, CIDR, scope (INTERNET / INTERNAL). The SG/NAU/IGW chain is the fix surface, not packages. |
| `CODE_VULNERABILITY` | **Lambda code defect.** Look at `CodeVulnerability` block: rule id, file path, line number, snippet. Source-level fix is required. Lambda-only. |
| `LAMBDA_CODE_VULNERABILITY` | **Lambda code defect** (alt label). Same handling as `CODE_VULNERABILITY`. |
| Mixed / unknown | Pull `batch-get-finding-details` and read the full JSON before classifying. |

### Severity short-circuit

| Severity | SLA guidance | Diagnostic change |
|---|---|---|
| `Critical` | Page / hours | Same root-cause walk; do NOT skip evidence. Verify against current state to rule out false positives. |
| `High` | Same-day remediation | Same walk. |
| `Medium` | Week | Same walk; batch with other findings. |
| `Low` | Backlog | Same walk; may be acceptable risk. |
| `Informational` | No SLA | SBOM or coverage metadata — usually not a remediation target. |

If the input is malformed (missing finding ARN, missing resource ARN,
ambiguous finding type, CVE id without a package name), emit `VERDICT:
NEED_MORE_INFO` with `FINDING_TYPE: UNKNOWN` and list the specific
missing fields. Re-prompt for: (1) the finding ARN or full JSON from
`batch-get-finding-details`, (2) the resource ARN (EC2/ECR/Lambda), and
(3) the time window of the finding's last observation.

## Process — Diagnostic decision tree (apply in finding-type order)

The diagnostic tree is finding-type-driven. Pick the entry point based on
the finding `Type`, then walk the type-specific probes in order. Each
layer ends with either a positive root-cause confirmation (failing probe
that matches the symptom) or a pass that moves to the next layer. **Never
emit ROOT_CAUSE_FOUND without a failing probe that matches the finding.**

### Step 0: Non-obvious behaviours that change diagnosis

Stale findings, exploitability conditions, layer-trace gotchas,
auto-close behaviour, redacted snippets — see
`references/advanced-patterns.md` § Step 0.

### Step 1: Finding entry — pick the diagnostic branch

Map the finding `Type` to a branch and jump to that branch's section.

| Type | Branch |
|---|---|
| `PACKAGE_VULNERABILITY` | Step 2 |
| `NETWORK_REACHABILITY` | Step 3 |
| `CODE_VULNERABILITY` / `LAMBDA_CODE_VULNERABILITY` | Step 4 |
| Ambiguous / multi-finding | Step 1b |

### Step 1b: Gather the full finding JSON (when the type is ambiguous)

Command: see `references/diagnostic-commands.md` § Step 1b.

The response includes the full finding JSON. Read `Type`, `Title`,
`Description`, and the type-specific block before classifying.

### Step 2: Package vulnerability — diagnose the vulnerable package

#### 2a: Package CVE on EC2 instance

Probes: see `references/diagnostic-commands.md` § Step 2a.

**Verdict signals:**
- `list-inventory-entries` shows the package in the CVE's vulnerable
  range, AND `fixedInVersion` is in the patch baseline →
  **ROOT_CAUSE_FOUND**, `LAYER: EC2_OS_PACKAGE`. Remediation: SSM Run
  Command `AWS-RunPatchBaseline` or `AWS-InstallMissingUpdates`.
- Instance NOT SSM-managed (no inventory) → **NEED_MORE_INFO**;
  operator must enable SSM agent or patch manually.
- Package version already >= `fixedInVersion` → finding is stale.
  **ROOT_CAUSE_FOUND**, `LAYER: STALE_FINDING`. Will auto-close on
  rescan.

#### 2b: Package CVE on ECR image

Probes: see `references/diagnostic-commands.md` § Step 2b.

**Verdict signals:**
- CVE present and image is referenced by a running task →
  **ROOT_CAUSE_FOUND**, `LAYER: ECR_BASE_IMAGE`. Remediation: rebuild
  with a patched base (`FROM` in Dockerfile), push, redeploy the task.
- Image old and not referenced by any running task →
  `LAYER: STALE_IMAGE`. Remediation: delete (`batch-delete-image`) or
  accept the risk; no running exposure.
- Vulnerable package is an application dependency (not the base image)
  → fix in the lockfile (`package-lock.json`, `requirements.txt`).

#### 2c: Package CVE on Lambda function

Probes: see `references/diagnostic-commands.md` § Step 2c.

**Verdict signals:**
- Layer version older than the patched version →
  **ROOT_CAUSE_FOUND**, `LAYER: LAMBDA_LAYER`. Remediation: publish a
  new layer version with the patched dependency; update the function.
- CVE in the deployment package (not a layer) →
  `LAYER: LAMBDA_DEPLOYMENT_PACKAGE`. Remediation: rebuild the zip
  with patched deps, `update-function-code`.
- CVE in the runtime itself (e.g., `nodejs20.x`) →
  `LAYER: LAMBDA_RUNTIME`. Remediation: update the function runtime;
  AWS manages runtime patches.

#### 2d: CVE without a fixed-in version

If `PackageVulnerability.fixedInVersion` is empty or null, the CVE has
no upstream fix yet. **ROOT_CAUSE_FOUND**,
`FINDING_TYPE: PACKAGE_VULNERABILITY`, `LAYER: NO_FIX_AVAILABLE`.
Remediation options: suppress the finding if not exploitable, isolate
the resource (restrict SGs, move to private subnet), or apply a
vendor mitigation (config change, WAF rule). Escalate to the package
maintainer.

### Step 3: Network reachability — diagnose the exposed port

#### 3a: SG rule exposes the flagged port

Probes: see `references/diagnostic-commands.md` § Step 3a.

**Verdict signals:**
- SG allows `0.0.0.0/0` on the flagged port →
  **ROOT_CAUSE_FOUND**, `LAYER: SG_OVERLY_PERMISSIVE`. Remediation:
  restrict the SG to a referenced SG or specific CIDR.
- SG allows a broad corporate CIDR (`10.0.0.0/8`) →
  `LAYER: SG_BROAD_CIDR`. Remediation: scope to the subnet or SG.
- SG already scoped → finding may be stale or via another path. Step 3b.

#### 3b: IGW route exposes the resource publicly

Probes: see `references/diagnostic-commands.md` § Step 3b.

**Verdict signals:**
- Instance has a public IP and the subnet route table has a `0.0.0.0/0`
  → an IGW → **ROOT_CAUSE_FOUND**, `LAYER: PUBLIC_IP_VIA_IGW`.
  Remediation: remove the public IP, move behind NAT/ALB, restrict SG.
- Private subnet but SG allows `0.0.0.0/0` → reachability is INTERNAL
  (the finding `scope` field distinguishes). Scope the SG regardless.

### Step 4: Lambda code vulnerability — diagnose the source defect

Probes: see `references/diagnostic-commands.md` § Step 4.

**Verdict signals:**
- `batch-get-code-snippets` returns a snippet matching the rule (e.g.,
  `child_process.exec` for command injection, hardcoded AWS key,
  `fs.readFile(req.query.path)` for path traversal) →
  **ROOT_CAUSE_FOUND**, `FINDING_TYPE: CODE_VULNERABILITY`,
  `LAYER: LAMBDA_SOURCE_DEFECT`. Remediation: fix the source code
  (sanitize input, remove hardcoded secret, validate path); redeploy
  the function.
- Snippet is `REDACTED` but the rule id + filePath identify the issue
  (e.g., rule `JS-DANGEROUS-SDK-USAGE`, file `handler.js`) → same
  verdict; operator must open the file manually.

### Step 5: SBOM export integration

Probes: see `references/diagnostic-commands.md` § Step 5.

**Verdict signals:**
- SBOM export maps the CVE'd package to multiple resources →
  **ROOT_CAUSE_FOUND**, `LAYER: SBOM_SCOPE`. Remediation: patch every
  resource in the SBOM that has the vulnerable package version;
  prioritize by severity and exposure.

### Step 6: Staleness check — finding already fixed

Probes: see `references/diagnostic-commands.md` § Step 6.

**Verdict signals:**
- Finding `State: OPEN` but current package version >= `fixedInVersion`
  → finding is stale; will close on next rescan.
  **ROOT_CAUSE_FOUND**, `LAYER: STALE_FINDING`. Remediation: trigger
  rescan or wait for the next cycle; no action needed.
- Finding `State: CLOSED` → already resolved; no action.

### Step 7: Escalate or NEED_MORE_INFO

If none of the above produced a positive root-cause match, OR the
finding is from a new Inspector detector without a documented
remediation path, emit one of:

- **ESCALATE** — AWS-side Inspector issue (e.g., a false-positive CVE
  that Inspector will not suppress, a code-vulnerability rule that
  fires on safe code). Surface the finding ARN, the rule id, and open
  a Support case.
- **NEED_MORE_INFO** — A specific probe requires operator input. List
  the missing pieces (SSM agent not enabled, ECR scan not configured,
  Lambda layer ARN unknown) and the next probe to run once the info is
  available.

## Output format

```text
TARGET: <resource-arn>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the finding type, the vulnerable artifact,
  and the failing probe that confirmed the cause>
FINDING_TYPE: <PACKAGE_VULNERABILITY | NETWORK_REACHABILITY |
               CODE_VULNERABILITY | UNKNOWN>
SEVERITY: <CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL>
LAYER: <EC2_OS_PACKAGE | ECR_BASE_IMAGE | LAMBDA_LAYER |
        LAMBDA_DEPLOYMENT_PACKAGE | LAMBDA_RUNTIME |
        LAMBDA_SOURCE_DEFECT | SG_OVERLY_PERMISSIVE | SG_BROAD_CIDR |
        PUBLIC_IP_VIA_IGW | SBOM_SCOPE | NO_FIX_AVAILABLE |
        STALE_FINDING | STALE_IMAGE | UNKNOWN>
EVIDENCE:
  - <observed finding — type, CVE, severity, last-observed time>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command — see references/finding-types-reference.md
     for copy-pasteable per-layer commands>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <resource-arn>. Proceed?
  (yes/no)"
```

### Worked example — Critical package CVE on EC2

```text
TARGET: arn:aws:ec2:us-east-1:111:instance/i-0abc123
VERDICT: ROOT_CAUSE_FOUND
REASON: Instance i-0abc123 has openssl-3.0.7 at version 3.0.7-1.amzn2023.1
  which is within CVE-2024-XXXX vulnerable range (< 3.0.8); the fixed
  version 3.0.8-1.amzn2023.1 is available in the SSM Patch Baseline.
FINDING_TYPE: PACKAGE_VULNERABILITY
SEVERITY: CRITICAL
LAYER: EC2_OS_PACKAGE
EVIDENCE:
  - Finding: PACKAGE_VULNERABILITY, CVE-2024-XXXX, severity CRITICAL,
    lastObservedAt 2026-08-09T18:00Z.
  - Probe: aws ssm list-inventory-entries --instance-id i-0abc123
    --type AWS:Application --filters Key=Name,Values=openssl
    returns Version: 3.0.7-1.amzn2023.1.
  - Probe: aws ssm describe-patches --filters Key=PRODUCT,
    Values=AmazonLinux2023 | jq '.[] | select(.CVEIds|
    contains("CVE-2024-XXXX"))' returns Version: 3.0.8-1.amzn2023.1.
  - Passing: instance is SSM-managed; SSM agent online; patch baseline
    assigned.
REMEDIATION:
  1. Apply the missing update via SSM Run Command (see references for
     full command).
  2. After the command completes, wait for the next Inspector scan; the
     finding auto-closes when the patched version is detected.
  3. Verify: aws ssm list-inventory-entries --instance-id i-0abc123
    --type AWS:Application --filters Key=Name,Values=openssl
    returns Version: 3.0.8-1.amzn2023.1.
CONFIRM: Before running AWS-RunPatchBaseline, emit and await:
  "CONFIRM: About to apply patches on i-0abc123 (openssl 3.0.7 -> 3.0.8).
   Proceed? (yes/no)"
```

Additional worked examples — Lambda hardcoded secret, SG overly
permissive: see `references/worked-examples.md`.

Finding triage priority matrix (exposure × severity): see `references/advanced-patterns.md` § Triage priority.

## Anti-Patterns — NEVER (top 5)

1. **NEVER declare ROOT_CAUSE_FOUND without a failing probe that matches
   the finding.** "Must be the package" without SSM inventory or ECR
   scan output erodes trust. Every verdict needs a confirming probe.

2. **NEVER confuse package vulnerability and reachability.** A
   `PACKAGE_VULNERABILITY` finding is fixed by patching the package;
   a `NETWORK_REACHABILITY` finding is fixed by restricting the SG or
   removing the public IP. The finding type tells you the fix surface.

3. **NEVER recommend patching a Lambda function's runtime for a code
   vulnerability.** Code vulnerabilities are source defects — the fix
   is in the application code. Updating the runtime does NOT close a
   code finding. Read the `CodeSnippet` first.

4. **NEVER manually close a finding that should auto-close on rescan.**
   Inspector sets `State: CLOSED` when a rescan confirms the issue is
   resolved. Manually closing creates audit noise. Use suppression
   (`update-configuration` → filter) ONLY for confirmed false positives.

5. **NEVER assume a Critical CVE is exploitable without checking the
   conditions.** Many CVEs have conditions: only on specific OS, only
   with a specific config, only if a vulnerable code path is called.
   A Critical CVSS score does not mean the vulnerability is reachable.
   Check the CVE description and upstream advisory first.

**Additional critical mistakes:** `list-findings` returns a summary (use
`batch-get-finding-details` for full JSON); never patch an ECR image in
place (rebuild); a Lambda layer CVE affects every function using the
layer ARN; never suppress without a documented reason; SBOM export is
separate from findings (use SBOM for scope, findings for action).

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`send-command`, `update-function-code`, `revoke-security-group-ingress`,
  `batch-delete-image`), emit and await operator approval.
- **Read-only first.** Every probe (`batch-get-finding-details`,
  `list-inventory-entries`, `describe-image-scan-findings`,
  `get-function-configuration`, `describe-security-groups`,
  `list-sbom-export`, `batch-get-code-snippets`) is read-only.
- **SSM patches may require a reboot.** Verify the instance has a
  maintenance window or is in an ASG that handles reboots.
- **Lambda updates cause a cold start** on the next invocation.
- **ECR image deletion is irreversible.** Verify no running task uses
  the image digest first.
- **SG changes affect all attached instances** — apply immediately.
- **Inspector rescan is throttled.** The next scan cycle is usually
  sufficient; avoid triggering immediate rescans.

For per-layer copy-pasteable remediation commands, see
`references/finding-types-reference.md`.

## References (load on demand)

- [Diagnostic commands](references/diagnostic-commands.md) — read-only probes per diagnostic step
- [Worked examples](references/worked-examples.md) — full walkthroughs
- [Advanced patterns](references/advanced-patterns.md) — non-obvious behaviours, triage matrix, 2024-2026 features
- [Finding types reference](references/finding-types-reference.md) — finding JSON format and per-layer remediation
- [Remediation CLI commands](references/remediation-cli-commands.md) — copy-pasteable state-changing commands per LAYER verdict

## Domain

AWS CloudOps / Inspector v2 Vulnerability Diagnostics, SBOM Integration,
Lambda Code Scanning, ECR Image Scanning, and SSM Patch Coordination.

Recent AWS features (SBOM export, Lambda code scanning, ECR enhanced scanning, deep inspection): see `references/advanced-patterns.md`.

## AWS documentation

- **Inspector User Guide** — https://docs.aws.amazon.com/inspector/latest/user/inspector_v2.html
- **Inspector finding types** — https://docs.aws.amazon.com/inspector/latest/user/findings.html
- **Inspector SBOM export** — https://docs.aws.amazon.com/inspector/latest/user/sbom-export.html
- **Inspector Lambda code scanning** — https://docs.aws.amazon.com/inspector/latest/user/lambda-code-scanning.html
- **Inspector ECR scanning** — https://docs.aws.amazon.com/inspector/latest/user/ec2-scanning.html
- **Inspector suppression filters** — https://docs.aws.amazon.com/inspector/latest/user/filters.html
- **AWS CLI Inspector v2** — https://docs.aws.amazon.com/cli/latest/reference/inspector2/
- **SSM Patch Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-patch.html
