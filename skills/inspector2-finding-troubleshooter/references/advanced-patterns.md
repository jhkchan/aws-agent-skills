# Advanced Patterns — Inspector v2 Edge Cases and Deep Dives

Operational gotchas, triage heuristics, and recent-feature notes
moved verbatim from SKILL.md for progressive disclosure.

### Step 0: Non-obvious behaviours that change diagnosis

These are operational gotchas a senior Inspector operator knows from
triage experience. Each routes a diagnosis away from the obvious layer:

- **A finding may be stale.** Inspector scans on a schedule (every 24h
  EC2, on push ECR, on update Lambda). A `lastObservedAt` > 24h may
  already be fixed. Check current state (SSM inventory, ECR scan,
  Lambda config) before recommending remediation.

- **A CVE may not be exploitable even if the package is present.** CVEs
  have conditions: only vulnerable with a specific config, OS, or code
  path. Check the upstream advisory before page-triggering on Critical.
  Suppress with `update-filter` if not applicable.

- **ECR image scans reflect the base image at build time.** A new image
  with a patched base closes the finding, but the running task is NOT
  patched until redeployed. Verify the task definition references the
  new image digest.

- **Lambda package CVEs live in layers.** A CVE in a shared layer
  affects every function using it. The fix is to publish a new layer
  version and update each function — not patch the function source.
  Use `get-function-configuration` → `Layers` to trace the CVE.

- **Lambda code scanning finds source defects, not package CVEs.**
  Inspector code scanning for Lambda (2024-2025) flags injection,
  hardcoded secrets, path traversal. The `CodeSnippet` from
  `batch-get-code-snippets` is the highest-signal artifact — it shows
  the exact line.

- **Reachability findings reflect SG + route + IGW state at scan time.**
  A port flagged internet-reachable may have been restricted since the
  scan. Verify with live `describe-security-groups` /
  `describe-route-tables`. If the SG is already scoped, the finding
  closes on the next scan — do NOT recommend redundant changes.

- **`batch-get-finding-details` is the single highest-signal command.**
  `list-findings` returns a summary; `batch-get-finding-details`
  returns the full JSON with the type-specific block. Always pull
  detail before classifying.

- **Findings auto-close on rescan if the issue is gone.** Inspector
  sets `State: CLOSED` automatically. Operators who "manually close"
  findings create noise — let Inspector close them. Manual suppression
  (`update-configuration` → filter) is for confirmed false positives.

- **Code snippets may be redacted.** `batch-get-code-snippets` redacts
  secrets (ironic for a hardcoded-secret finding). The `text` field may
  show `REDACTED` — use `filePath` + `lineNumber` to locate manually.

## Expert heuristic: finding triage priority

Inspector emits findings by severity, but the *exploitability* and
*exposure* of the vulnerable resource determines the actual priority.
Triage by exposure first, severity second, exploitability third.

| Exposure + severity | Priority | Action |
|---|---|---|
| Public IP + Critical CVE | P0 | Patch within hours; isolate if no fix |
| Public IP + High CVE | P1 | Patch same day |
| Internal + Critical CVE | P1 | Patch same day; isolate if no fix |
| Internal + High CVE | P2 | Patch within the week |
| Reachability Critical (any port) | P0 | Restrict SG within hours |
| Reachability Medium (internal port) | P3 | Backlog; scope when possible |
| Code vuln (hardcoded secret) | P0 | Rotate + fix immediately |
| Code vuln (path traversal) | P1 | Fix same day |
| Stale finding (already patched) | — | Verify and let auto-close |

**Common mistake:** triaging by severity alone. A Critical CVE on a
fully-isolated instance with no public IP and no exploitable code path
is a P2. A High CVE on an internet-facing instance with a known exploit
in the wild is a P0. The skill surfaces the exposure (public IP, SG
scope) alongside the severity.

## Recent AWS features (2024-2026)

- **Inspector SBOM export (2024-2025):** Software Bill of Materials
  (CycloneDX or SPDX) for an account or resource. Exported to S3 with
  full package inventory across EC2, ECR, Lambda. Use SBOM to map a
  CVE to all affected resources, not just the flagged one.
- **Inspector code scanning for Lambda (2024-2025):** SAST-style code
  vulnerability detection for Lambda functions (injection, hardcoded
  secrets, path traversal, weak crypto). Uses `batch-get-code-snippets`
  to return the exact source line. Findings: `Type: CODE_VULNERABILITY`
  or `LAMBDA_CODE_VULNERABILITY`. Requires enabling on the account.
- **Lambda layer scanning (2024-2025):** Inspector scans attached Lambda
  layers for package CVEs, not just the deployment package. A CVE in a
  shared layer produces findings on every function using it. The layer
  ARN is in `get-function-configuration`.
- **ECR enhanced scanning (2024):** Deeper container CVE coverage beyond
  the native ECR scan. Toggle per-repo via
  `put-image-scanning-configuration` with `scanType=ENHANCED`.
  Findings flow to both ECR and Inspector.
- **Inspector v2 EC2 deep inspection (2024-2025):** Extended package
  coverage for EC2 (application-level packages, not just OS). Requires
  SSM agent. `list-coverage` shows the deep inspection status.
- **Inspector finding aggregation to Security Hub (2024-2025):**
  Findings forward to Security Hub for cross-service triage.
