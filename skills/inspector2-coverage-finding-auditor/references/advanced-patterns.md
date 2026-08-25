# Inspector2 Coverage + Finding Auditor — advanced patterns (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Philosophy — extended rationale (absence of evidence)

**Absence of evidence is not evidence of absence.** Inspector2's dashboard
can show "no findings" for two radically different reasons: (a) the resource
was scanned and is clean, or (b) the resource was never scanned so nothing
could be found. This skill resolves that ambiguity by verifying coverage
FIRST, then evaluating findings. A verdict is only as trustworthy as the
coverage that produced it — a CRITICAL CVE on an unscanned instance is
invisible, and the skill must surface the coverage gap itself as the risk.

## Step 1 — intro (coverage requires enrollment + recency)

For each resource in the input, determine coverage using the type-specific
criteria. Coverage is NOT just "Inspector2 is enabled" — it requires that
the resource is actually enrolled and recently scanned.

## Step 1 — EC2 coverage conditions (detail)

1. The instance is in `running` state. Inspector2 does NOT scan stopped
   instances — a stopped instance retains its last-known findings but is
   not re-evaluated. Treat a stopped instance as UNCOVERED (the stale
   findings do not reflect the current AMI/package state when the
   instance is next started). If the input shows `State: stopped` or
   `State: stopped` in the EC2 metadata, coverage is inactive.
2. The SSM agent is running on the instance and the instance is
   SSM-managed (`PingStatus: Online` in
   `aws ssm describe-instance-information`). Inspector2 delegates EC2
   scanning to the SSM agent — no SSM agent = no scan, period.
3. Inspector2 EC2 scanning is `ENABLED` (Step 0).
4. `lastScannedAt` is within **7 days** (Inspector2 continuously rescans
   EC2 instances; a stale timestamp means the agent stopped reporting or
   the instance was stopped and restarted). If `lastScannedAt` is `null`,
   empty, or absent, the instance has NEVER been scanned — treat as
   UNCOVERED (not ACTIVE).

## Step 1 — ECR coverage conditions (detail)

1. Inspector2 ECR scanning is `ENABLED` (Step 0). If DISABLED, ALL ECR
   images in the region are UNCOVERED — skip remaining checks.
2. The repository has `scanOnPush: true` (images are scanned automatically
   on push) OR the specific image has a recent `scanStatus` (scanned
   within 30 days via manual trigger). If `scanOnPush: false` and no
   recent manual scan exists, the repo/image is **UNCOVERED**.
3. `lastScannedAt` is within **30 days** for ACTIVE coverage. If
   `lastScannedAt` is `null` or absent, the image has never been scanned —
   treat as UNCOVERED (not ACTIVE).

## Step 1 — ECR rescan limitation note

Note: ECR images are NOT continuously rescanned like EC2 instances — a CVE
published after the image was pushed will NOT be detected unless the image
is re-scanned or re-pushed. This is a critical coverage limitation for
production images. ECR enhanced scanning (Inspector2 continuous rescans)
re-evaluates images against the latest CVE database without requiring a
re-push — if enhanced scanning is enabled, treat the coverage as ACTIVE
regardless of lastScannedAt age (Inspector2 is continuously re-checking).

## Step 1 — Lambda coverage conditions (detail)

1. Inspector2 LAMBDA scanning is `ENABLED`.
2. For code-level vulnerabilities (dependency analysis), LAMBDA_CODE
   scanning must also be `ENABLED`. Standard Lambda scanning only covers
   the runtime environment, not the function code or its dependencies.

If standard scanning is on but code scanning is off, coverage is
**PARTIAL** — treat as MEDIUM coverage gap at most (the function's code
dependencies are not checked for known CVEs).

## Step 2 — compliance-tag note and SSM expert note

**Compliance tags do NOT independently escalate severity.** A `compliance=pci`
tag classifies the resource as SENSITIVE tier (which maps to the
PRODUCTION/SENSITIVE column above), but it does NOT add additional severity
levels beyond the matrix. A PCI-tagged ECR repo with a MEDIUM CVE and
STALE_MODERATE coverage is MEDIUM — not HIGH — because the matrix says
STALE_MODERATE + PRODUCTION/SENSITIVE = MEDIUM.

**Expert note on the SSM dependency:** the single most common cause of
false "COVERED" verdicts is an EC2 instance where Inspector2 EC2 scanning
is enabled but the SSM agent is not running. The Inspector2 console shows
the instance as "registered" (because it exists in the account) but no
scans run. Always check `ssm describe-instance-information --query
'InstanceInformationList[?PingStatus==`Online`]'` — if the instance is not
in that list, it is uncovered regardless of Inspector2 settings.

## Step 3 — finding filters (detail)

1. **Only OPEN findings count.** Inspector2 finding lifecycle:
   - `OPEN` — active, needs remediation. COUNTS toward verdict.
   - `SUPPRESSED` — auto-suppressed by Inspector2 (package removed from
     image/instance) or manually suppressed. Does NOT count. These are
     resolved.
   - `CLOSED` — manually resolved or auto-closed after fix verification.
     Does NOT count.
2. **INFORMATIONAL findings do not escalate.** Inspector2 emits
   INFORMATIONAL findings for reachability notes and non-vulnerability
   observations. A resource with only INFORMATIONAL findings is COVERED.
3. **De-duplicate by package+version.** The same CVE in the same package
   version across multiple finding IDs counts as ONE finding. Inspector2
   may emit multiple finding records for the same vulnerability across
   different scan paths — aggregate by `packageVulnerabilityId` or
   `cve` + `affectedPackage` + `affectedVersion`.
4. **Check `fixAvailable` for remediation triage.** Each Inspector2 finding
   includes a `fixAvailable` boolean. If `true`, a patched version of the
   vulnerable package exists and the remediation is straightforward (patch
   or upgrade). If `false`, no upstream fix exists yet — the finding
   cannot be resolved by patching alone. For `fixAvailable: false` on a
   CRITICAL or HIGH finding, note in REMEDIATION that a compensating
   control (WAF rule, network isolation, runtime patch) is required until
   the upstream project ships a fix. This does not change the verdict
   severity, but it changes the remediation guidance fundamentally.
5. **Check `inspectorScore` and `exploitabilityDetails`.** Beyond CVSS,
   Inspector2 provides an `inspectorScore` that adjusts the base CVSS
   based on AWS-specific reachability data, and `exploitabilityDetails`
   that indicates if a known exploit exists. If
   `exploitabilityDetails.lastKnownExploitInDays` is present and low
   (< 30 days), the vulnerability is being actively exploited — treat
   identically to a CISA KEV listing (escalate to CRITICAL per Step 4).

## Step 4 — reachability amplification prose and staleness caveat

Each OPEN finding has a `severity` field from Inspector2 (CRITICAL, HIGH,
MEDIUM, LOW) based on CVSS v3 scoring. But CVSS alone does not capture
exploitability in YOUR environment. Apply the **reachability amplification
escalation** — the core expert delta:

**Network reachability cross-reference:**

Inspector2 emits `NETWORK_REACHABILITY` findings that describe what is
reachable from the internet or internal network. Cross-reference each
package/code vulnerability finding against reachability findings for the
same resource:

- If the resource has a `NETWORK_REACHABILITY` finding with
  `protocol: TCP` and `portRange` matching the vulnerable service port,
  AND `reachability: ReachableFromInternet` → the CVE is **internet
  exploitable**. Escalate severity by one level (MEDIUM→HIGH,
  HIGH→CRITICAL).
- If the reachability is `ReachableFromInternalNetwork` (reachable from
  other instances in the VPC but not the internet) → do NOT escalate,
  but note the lateral-movement risk in REMEDIATION.
- If no reachability finding exists, assume the CVE is NOT internet
  exploitable (keep base severity). The absence of a reachability finding
  means Inspector2 did not detect an open path — this is generally
  reliable for EC2 but may miss application-layer exposure.

**Reachability staleness caveat:** NETWORK_REACHABILITY findings are
point-in-time assessments snapshotting the security-group and route-table
state at scan time. If the SG was modified after the reachability finding
was generated (check CloudTrail for recent
`AuthorizeSecurityGroupIngress` / `RevokeSecurityGroupIngress` events),
the reachability data may be stale. Before escalating based on a
reachability finding, note its age: if the finding is older than the most
recent SG change, mark the reachability as UNVERIFIED in the REASON field
and keep the base severity. Do NOT blindly escalate on stale reachability
data — a false "internet-reachable" escalation triggers unnecessary
incident-response.

## Steps 5-7 — taxonomy and aggregation (detail)

### Step 5: Finding type taxonomy and severity context

Inspector2 finding types carry different risk profiles beyond their CVSS:

- **PACKAGE_VULNERABILITY** — a CVE in an installed package (OS-level or
  application dependency). Severity is CVSS-based. These are the most
  common finding type for EC2 and ECR.
- **CODE_VULNERABILITY** — a vulnerability in Lambda function code
  (detected by Lambda code scanning). These are application-level issues
  (hardcoded secrets, insecure deserialization, SQL injection). Severity
  is assigned by Inspector2's static analysis, not CVSS.
- **NETWORK_REACHABILITY** — describes network paths, not vulnerabilities
  per se. Used as an amplification signal (Step 4), not a standalone
  severity driver.
- **MISCONFIGURATION** — Inspector2 detects security misconfigurations
  (e.g., public S3 bucket, overly permissive SG). These map to the
  security-auditor skills (s3-public-access-auditor,
  ec2-security-group-auditor) for deep classification. For this skill, a
  MISCONFIGURATION finding's severity is taken from Inspector2's
  classification.

### Step 6: Resource-level aggregation

A resource may have multiple findings AND a coverage state. The
resource-level verdict is the **worst** of:

1. The coverage gap severity (Step 2), if any.
2. The highest escalated finding severity (Step 4), if any open findings.

Where CRITICAL > HIGH > MEDIUM > LOW > COVERED.

If the resource has ACTIVE coverage (Step 1) AND zero OPEN findings above
INFORMATIONAL, the verdict is **COVERED** — the sole "safe" state.

### Step 7: Account/region-level aggregation

When auditing an entire account or region, aggregate across all resources:

1. Collect all resource-level verdicts.
2. The account/region verdict is the **worst** verdict across all
   resources.
3. In the output, list each resource with its individual verdict, then the
   aggregate.

A single CRITICAL resource makes the entire account CRITICAL. This is
intentional — one exploitable vulnerability is an active breach path.

## Effective coverage context — expert notes

1. **SSM Agent enrollment** — EC2 instances must be enrolled in Systems
   Manager. This requires the SSM agent to be installed (default on
   Amazon Linux 2/2023, Ubuntu 16.04+, needs manual install on other
   AMIs), the instance to have an IAM role with
   `AmazonSSMManagedInstanceCore`, and outbound connectivity to SSM
   endpoints (direct, via NAT gateway, or via VPC endpoints for
   air-gapped VPCs).
2. **Region enablement** — Inspector2 is regional. Enabling it in
   us-east-1 does NOT cover resources in eu-west-1. In a multi-region
   account, verify each region where resources exist. A common gap:
   Inspector2 enabled in the "primary" region but resources deployed in
   a "secondary" region for latency or DR.
3. **Organizations delegated admin** — in AWS Organizations, Inspector2 is
   configured from a delegated admin account. Member accounts inherit the
   configuration, but a member account can independently disable
   scanning (unless restricted by the admin). Always check per-account
   status, not just the delegated admin.
4. **ECR re-scan gap** — unlike EC2 (continuously scanned), ECR images are
   scanned once at push time (if `scanOnPush: true`). A CVE published
   after the push will NOT be detected until the image is re-scanned or
   re-pushed. For production images that are rarely rebuilt, this is a
   silent coverage degradation. Enable ECR enhanced scanning (Inspector2
   continuous rescans) or schedule periodic re-scans for production repos.
5. **Stopped instances** — Inspector2 does not scan stopped EC2 instances.
   A stopped instance retains its findings from the last scan but is not
   re-evaluated. If the instance is started later, Inspector2 resumes
   scanning — but the gap during the stopped period is invisible.
6. **`lastScannedAt` is scan START, not completion** — the timestamp
   records when Inspector2 began the assessment, not when it finished.
   For instances with large package inventories (>500 installed packages),
   the full assessment can take 10-30 minutes. A resource with
   `lastScannedAt: 2026-08-04T10:00:00Z` and zero findings at
   `2026-08-04T10:05:00Z` may simply not have completed the scan yet.
   If the timestamp is very recent (< 30 minutes), note in the output:
   "scan may still be in progress — zero findings is preliminary."
7. **ListFindings pagination** — `aws inspector2 list-findings` returns
   max 100 findings per page. Large accounts with thousands of findings
   MUST paginate (`--next-token`). When the input provides findings data,
   verify that it represents a complete set, not just the first page. If
   the finding count seems abnormally low for a large production fleet,
   note: "finding data may be truncated — verify pagination was applied."
8. **Fargate coverage gap** — Inspector2 does NOT independently scan
   container images running on Fargate. Coverage depends entirely on the
   ECR repo having scanning enabled. A Fargate task running an image from
   an ECR repo with `scanOnPush: false` has NO vulnerability scanning,
   even if Inspector2 EC2 and ECR are both "enabled" at the account level.
   When auditing container workloads, always trace back to the source ECR
   repo's scanning configuration.
9. **Finding eventual consistency** — after patching a vulnerability, the
   Inspector2 finding remains OPEN until the next scan cycle completes
   (typically within 24 hours for EC2, immediately for ECR on re-push).
   Do NOT classify a resource as still vulnerable based on a finding that
   predates a known patch application. If the input indicates the patch
   was applied but the finding is still OPEN, note: "finding may be stale
   — next scan cycle will confirm remediation."
10. **`inspectorScore` NULL for new CVEs** — when a CVE is newly published,
    AWS's internal analysis may not have completed yet, leaving
    `inspectorScore` as NULL while the `severity` field shows a
    preliminary rating. In this case, fall back to the raw CVSS score for
    severity classification and note: "inspectorScore pending — using NVD
    CVSS as fallback." This is common for CVEs published within the last
    48 hours.

## Expert decision tree — Inspector2-specific edge cases

These are scenarios where a capable model's general knowledge of
vulnerability scanning is insufficient. The correct classification requires
Inspector2-specific internal behavior:

**Q: An EC2 instance shows coverage `ACTIVE` but has zero findings AND zero
reachability findings. Is it COVERED?**

Not necessarily. If the SSM agent is online but the Inspector2 assessment
has never completed a full scan cycle (the `lastScannedAt` is null or
matches the enrollment timestamp), the instance is enrolled but not yet
assessed. Inspector2's initial assessment can take 10-30 minutes after
enrollment. During this window, the instance has ACTIVE status but no
meaningful finding data. Classify as **MEDIUM** (coverage pending), not
COVERED.

**Q: An ECR repo has `scanOnPush: true` but the image was pushed 6 months
ago. The scan shows zero findings. Is it COVERED?**

No. ECR basic scanning evaluates the image at push time only. CVEs
published in the last 6 months are invisible. The `lastScannedAt`
timestamp is stale (STALE_SEVERE per Step 1). Recommend ECR enhanced
scanning (Inspector2 continuous rescans) which re-evaluates images against
the latest CVE database without requiring a re-push. Classify as **HIGH**
if production, **MEDIUM** otherwise.

**Q: A Lambda function has standard scanning ENABLED and code scanning
DISABLED. It has zero findings. Is it COVERED?**

No — it has PARTIAL coverage. Standard Lambda scanning checks the runtime
environment (the managed AWS runtime, e.g., `nodejs20.x`) but NOT the
function's deployment package or layers. If the function imports a
vulnerable npm package or Python library, that CVE is invisible without
code scanning. Classify as **MEDIUM** for production functions, **LOW** for
non-production. The remediation is to enable LAMBDA_CODE scanning.

**Q: A finding has `status: OPEN` but the `packageVulnerabilityId` matches
a finding that was SUPPRESSED on a different resource. Is it still OPEN?**

Yes — suppression is per-resource, not per-CVE. If `log4j-core 2.14.1` is
SUPPRESSED on instance A (because the package was removed from A's AMI) but
still OPEN on instance B (where the package is still installed), the finding
on B remains OPEN and actionable. Do not propagate suppression status
across resources. De-duplicate by CVE+package+version for counting, but
evaluate `status` independently per resource.

**Q: A resource has both a CRITICAL CVE finding and a DENY in its security
group (no inbound traffic). Is the CVE still CRITICAL?**

Yes. The CVE severity is based on the vulnerability, not the current
network exposure. However, the reachability amplification (Step 4) would
NOT escalate because there is no `ReachableFromInternet` finding (the SG
denies inbound). The base CRITICAL severity (CVSS >= 9.0) stands — a
future SG change could expose the vulnerability. Note the SG-based
mitigation in REMEDIATION as a containment measure, but the verdict remains
CRITICAL because the vulnerable package is still installed.

**Q: An EC2 instance is in an Auto Scaling Group that regularly replaces
instances. Are the findings from the old instance still valid?**

No. Findings are tied to the specific instance ID. When an ASG replaces an
instance, the old instance's findings are auto-suppressed (the instance no
longer exists). The new instance gets fresh findings after Inspector2
completes its initial scan. However, if the AMI or launch template contains
the same vulnerable packages, the new instance will produce the same
findings — the root cause is the AMI, not the instance. Recommend patching
the AMI/launch template, not individual instances.

**Q: The `inspectorScore` differs from the NVD CVSS score for the same
CVE. Which one drives the severity?**

Inspector2's `inspectorScore` adjusts the base NVD CVSS based on
AWS-internal reachability and runtime context. For example, a CVE with
CVSS 9.0 might have `inspectorScore: 7.0` if AWS determines the vulnerable
code path is unreachable in the specific AMI/kernel combination. Use the
`inspectorScore` (not raw CVSS) when determining the finding's effective
severity — it is more accurate for YOUR specific environment. However, the
`severity` field (CRITICAL/HIGH/MEDIUM/LOW) is already derived from the
inspectorScore, so in practice you use the `severity` field directly.
Expert nuance: if `inspectorScore` is significantly lower than CVSS (>= 2
points), note in REMEDIATION that AWS's runtime analysis reduced the
effective risk — but the vulnerable package should still be patched to
eliminate the residual risk.

**Q: A multi-architecture ECR image (amd64 + arm64) has a CVE only in the
arm64 manifest. Does scanOnPush catch it?**

Yes, but only if both manifests are present. Inspector2 scans each
manifest independently. A CVE in only the arm64 variant produces a finding
scoped to that manifest digest. When auditing ECR coverage, verify that
the `imageDigest` in the finding matches the manifest actually deployed.
A common gap: teams deploy the amd64 image (clean) but the arm64 image
(used by Graviton instances) has unpatched CVEs that go unnoticed because
the audit only checked the default manifest.

**Q: A Lambda function imports a vulnerable Lambda Layer. Is the function
covered by Inspector2?**

Partially. Inspector2 Lambda code scanning evaluates the function's
deployment package, but Lambda Layers are scanned as part of the function
that imports them — not independently. If a shared Layer has a CVE, every
function consuming that Layer inherits the finding. When auditing Lambda
coverage, check for shared Layers across functions: a single vulnerable
Layer can amplify impact across dozens of functions. The remediation is
to patch the Layer and update all consuming functions to the new Layer
version.

**Q: The Inspector2 delegated admin account was removed from AWS
Organizations. What happens to member-account coverage?**

All member accounts lose their Inspector2 configuration within 24 hours
of the delegated admin removal. Existing findings remain (they are
per-account resources) but no new scans run. This is a silent coverage
collapse — there is no finding or alert for it. If the input shows
Inspector2 was recently configured via delegated admin and the admin
account status is unknown, verify each member account independently with
`aws inspector2 batch-get-account-status` per account. A recently
disrupted delegation is one of the highest-impact coverage gaps because
it affects ALL resource types across ALL member accounts simultaneously.

**Q: A finding has `fixAvailable: false` on a CRITICAL CVE. How should
this change the verdict and remediation?**

The VERDICT does not change — the CVE is still CRITICAL severity and the
vulnerable package is still installed. However, the REMEDIATION must
shift from "patch the package" to "apply compensating controls":
restrict the security group to deny inbound on the vulnerable port, add
a WAF rule to block exploit signatures, or deploy a runtime patch
(e.g., hot-patching the vulnerable function via LD_PRELOAD or a
sidecar interceptor). Note in REMEDIATION: "No upstream fix available —
compensating control required until CVE is patched upstream. Monitor
the upstream project for a fix release." This is a critical distinction:
`fixAvailable: false` means the normal patch workflow will NOT resolve
the finding, and the reviewer must know this to plan remediation
correctly.

## Recent AWS features, external references, and section taxonomy

- **Lambda function code scanning (2024):** Inspector now scans Lambda function code (not just packages) for vulnerabilities. This adds `LambdaFunctionCode` as a scan type. Auditors should verify that Lambda code scanning is enabled in the Inspector2 configuration — it is a separate enablement flag from Lambda package scanning.
- **SBOM export (2024):** Inspector can now export Software Bill of Materials (SBOM) in CycloneDX format for EC2, ECR, and Lambda resources. Auditors should verify that SBOM export is configured for compliance-sensitive workloads.
- **Amazon Q vulnerability remediation (2024-2025):** Inspector integrates with Amazon Q for AI-driven vulnerability remediation suggestions. No new audit-surface fields, but auditors should note that remediation tracking now includes Q-generated fix suggestions.
- **Enhanced network reachability analysis (2024):** Inspector's network reachability analysis now includes broader coverage of security group configurations and ENI attachment states. Auditors should verify that network reachability findings are correlated with current security group state (not stale SG rules).
- **Deep inspection GA (2024-2025):** Inspector Deep Inspection scans all packages on EC2 instances (not just OS-level). Auditors should verify that Deep Inspection is enabled for production instances — it requires SSM Agent and additional configuration.

## References

- AWS Inspector2 Documentation: coverage statistics, finding types, and
  API reference for `ListCoverage`, `ListFindings`,
  `BatchGetAccountStatus`.
- CISA Known Exploited Vulnerabilities (KEV) catalog:
  `https://www.cisa.gov/known-exploited-vulnerabilities-catalog` —
  cross-reference CVE IDs against this catalog for real-world
  exploitability escalation.
- MITRE ATT&CK technique mapping: Inspector2 MISCONFIGURATION and
  NETWORK_REACHABILITY findings map to ATT&CK techniques for threat-model
  correlation.

## Section taxonomy (CloudOps auditor pattern)

This skill follows the CloudOps auditor skill pattern, with sections in
this canonical order:

1. **Frontmatter** — name, description, version, metadata.
2. **Quick reference** — three core rules.
3. **Mindset** — the two-axis (coverage + severity) reasoning framework.
4. **Philosophy** — guiding principle (verify coverage before trusting
   findings; verdict vs FINDINGS count separation).
5. **Decision flow summary** — high-level 6-step classification flow.
6. **Classification logic** — ordered decision tree (Steps 0-7) with
   inline matrices and edge-case handling.
7. **Output format** — per-resource template, field rules, FINDINGS
   counting rules, worked examples, and account-level aggregation.
8. **NEVER** — anti-patterns with explicit reasoning.
9. **Pre-flight safety checks** — destructive-operation constraints.
10. **Remediation guidance** — per-verdict action table.
11. **References** — CISA KEV, ATT&CK, Inspector2 API.
