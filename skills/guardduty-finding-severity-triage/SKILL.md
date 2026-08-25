---
name: guardduty-finding-severity-triage
description: Classifies Amazon GuardDuty findings into a context-aware triage severity (CRITICAL | HIGH | MEDIUM | LOW | LIKELY_FALSE_POSITIVE) by overlaying finding-type threat taxonomy, false-positive signals, aggregation counts, and resource criticality on top of GuardDuty's numeric severity. Detects authorized-scanner port sweeps, Tor traffic to public services, known-safe DNS domains, and AWS service-linked role activity as false-positives. Provides per-verdict incident-response remediation steps. Use when triaging GuardDuty findings (JSON or structured text) for SOC prioritization, false-positive filtering, or escalation decisions.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf). No AWS CLI required for offline finding classification — the skill reasons over provided finding JSON or structured text. Live-account triage uses aws guardduty list-findings / get-findings and aws guardduty archive-finders (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: CRITICAL | HIGH | MEDIUM | LOW | LIKELY_FALSE_POSITIVE
  when_to_use: Triage a GuardDuty finding (JSON or structured text) to determine its real-world response priority, check whether a finding is a likely false-positive (authorized scanner, known-safe DNS, public service Tor traffic), decide which findings to escalate to incident response, prioritize findings for a SOC queue, or determine whether to archive or suppress a recurring finding pattern.
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: GuardDuty, finding severity, threat triage, false positive, PortSweepUnusual, TorIPCaller, CryptocurrencyClient, SSHBruteForce, MaliciousIPCaller, credential exfiltration, suppression filter
  tags: guardduty, security, threat-detection, triage, false-positive, incident-response, mitre-attack
---

# GuardDuty Finding Severity Triage

## Triage in 30 seconds (start here)

Run this decision tree in order. Stop at the first match.

1. **Input valid?** Missing `type`, `severity`, or `resource` → `VERDICT: ERROR`
2. **False positive?** Matches Step 1 patterns FP-1 through FP-6 → `LIKELY_FALSE_POSITIVE`
3. **Active compromise?** Crypto mining, data exfiltration, credential exfiltration outside AWS, confirmed C2, ransomware, `HostLost` → `CRITICAL`
4. **Strong compromise indicator?** Malicious IP caller, SSH/RDP brute force, backdoor, privilege escalation → `HIGH`
5. **Behavioral anomaly?** Anomalous console login, unknown-source port sweep, unusual discovery → `MEDIUM`
6. **Reconnaissance?** Port probe, low-severity DNS → `LOW`
7. **Unknown type?** Fall back to numeric severity band (8.0+ HIGH, 5.0-7.99 MEDIUM, 1.0-4.99 LOW)

Then apply context overlays (Step 7): count-based escalation, resource-criticality escalation.

**Compact severity map** (finding-type prefix to default verdict, before context overlays):

| Threat purpose | Default verdict | Override |
|---|---|---|
| `Impact:*` (mining, DDoS, ransomware) | CRITICAL | FP-1 if authorized scanner (rare) |
| `Exfiltration:*` | CRITICAL | None — always investigate |
| `Backdoor:EC2/CC*` (confirmed C2) | CRITICAL | None |
| `UnauthorizedAccess:*MaliciousIP*` | HIGH | FP-4 if Tor on public service |
| `UnauthorizedAccess:*BruteForce*` | HIGH | None |
| `Backdoor:IAMUser/*` | HIGH | None |
| `PrivilegeEscalation:*` | HIGH | None |
| `*AnomalousBehavior` (ML) | MEDIUM | FP-6 if change window |
| `Recon:EC2/PortSweepUnusual` | MEDIUM | FP-1/FP-2 if scanner/LB |
| `Recon:EC2/PortProbe*` | LOW | Check exposed port |
| `Recon:IAMUser/*` (recon tier) | LOW | FP-5 if AWS service role |

**Critical safety rules (read before any action):**

- Never auto-archive `Impact:*` findings — crypto-mining and DDoS findings are CRITICAL until verified.
- Never classify `InstanceCredentialExfiltration.OutsideAWS` as below CRITICAL.
- Never terminate a compromised instance before isolating and snapshotting — termination destroys forensic evidence.
- Never create a suppression filter scoped to a finding TYPE without an IP/resource constraint — this silently disables threat detection for an entire attack class.
- Never downgrade a verdict based solely on GuardDuty's confidence score.

Full details for each step, false-positive pattern, and rule are in the sections below.

## Mindset

Full mindset framing moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Mindset — full triage framing

## Process — Classification logic (apply in order)

### Step 0: Validate finding input

If the finding is missing `type` (the finding-type string, e.g.,
`Recon:EC2/PortSweepUnusual`), `severity` (numeric 1.0-10.0), or
`resource` (at least a resource type), output:

```text
FINDING: <id or type>
VERDICT: ERROR
REASON: Finding input is incomplete — missing type, severity, or resource. Cannot triage.
REMEDIATION: Re-fetch the finding: aws guardduty get-findings --detector-id <id> --finding-ids <fid>.
```

Do not attempt classification without the finding type. The finding type
encodes the threat purpose, resource type, and family — without it, any
verdict is a guess.

Malformed-JSON edge-case handling moved to references.
→ [references/error-handling.md](references/error-handling.md) § Malformed finding JSON handling

Stale-finding and naming-convention checks moved to references.
→ [references/error-handling.md](references/error-handling.md) § Stale findings and finding-type naming convention

### Step 1: False-positive override (evaluate FIRST — highest priority)

Before applying any severity classification, check whether the finding
matches a known false-positive pattern. False-positive context overrides
numeric severity — a severity-8.0 finding from an authorized scanner is
still a false positive.

Quick FP check summary moved to references.
→ [references/false-positive-patterns.md](references/false-positive-patterns.md) § Quick FP check

Detailed FP-1..FP-6 pattern definitions moved to references.
→ [references/false-positive-patterns.md](references/false-positive-patterns.md) § Detailed false-positive patterns FP-1 through FP-6

### Step 2: CRITICAL — active compromise (immediate IR required)

Step 2 band rationale moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Step 2 intro — why active-compromise types are CRITICAL

**CRITICAL finding types:**

- `Impact:EC2/CryptocurrencyClient` — confirmed crypto-mining client on
  the instance. The instance is being used for crypto mining; the attacker
  has command execution. Immediate isolation required.
- `Impact:EC2/BitcoinTool.B` — Bitcoin-related tooling detected. Same
  response as CryptocurrencyClient.
- `Impact:EC2/AbusedThroughDDoS` — the instance is being used as a DDoS
  participant (botnet node). The instance is actively attacking external
  targets.
- `Impact:EC2/DDoSAggressiveProtocol` — aggressive protocol abuse
  consistent with DDoS participation.
- `Impact:EC2/HostLost` — GuardDuty has determined the host is lost
  (compromised). This is GuardDuty's strongest compromise signal.
- `Impact:EC2/Gpcode` — ransomware-family activity detected.
- `Exfiltration:EC2/*` — confirmed data exfiltration from an EC2 instance.
  Data is leaving the account to an unauthorized destination.
- `Exfiltration:IAMUser/*` — confirmed data exfiltration via IAM
  credentials.
- `Exfiltration:S3/*` — confirmed data exfiltration from an S3 bucket.
- `UnauthorizedAccess:EC2/InstanceCredentialExfiltration.OutsideAWS` —
  EC2 instance credentials are being used from outside AWS. The instance
  profile's temporary credentials have been stolen and are being used by
  an external attacker. This is one of the most dangerous findings — the
  attacker can access any resource the instance role can access.
- `Backdoor:EC2/CC*` — confirmed command-and-control (C2) communication.
  The instance is communicating with a known C2 server.
- `DefenseEvasion:EC2/AssumedRoleAccessKeyDeleteOrDisable` — an attacker
  is deleting or disabling access keys to cover their tracks after
  compromise. This is a post-exploitation IR indicator.
- `Persistence:EC2/AnomalousBehavior` when paired with indicators of
  web-shell or backdoor installation (check `service.additionalInfo` for
  `shellHistory`, `newUserCreated`, or `sshKeyAdded` signals).

Escalation rationale moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Severity escalation to CRITICAL (from HIGH numeric)

### Step 3: HIGH — strong compromise indicator (investigate within hours)

If the finding type is in the HIGH list below, output **HIGH**. These
findings indicate a likely compromise or unauthorized access that requires
prompt investigation. They are not yet confirmed active threats (that
would be CRITICAL), but they are too urgent to queue for routine
investigation.

**HIGH finding types:**

- `UnauthorizedAccess:IAMUser/MaliciousIPCaller` — API call from a
  known-malicious IP address. The IAM credentials may be compromised.
- `UnauthorizedAccess:IAMUser/MaliciousIPCaller.Custom` — API call from
  an IP on your custom threat list.
- `UnauthorizedAccess:EC2/SSHBruteForce` — SSH brute-force attack against
  an EC2 instance. Even at GuardDuty severity ~7.0 (MEDIUM), escalate to
  HIGH because a successful brute-force leads to instance compromise.
- `UnauthorizedAccess:EC2/RDPBruteForce` — RDP brute-force. Same
  escalation reasoning as SSH.
- `UnauthorizedAccess:EC2/MetadataDNSRebind` — SSRF attack using DNS
  rebinding to access instance metadata. Can lead to credential theft
  via the IMDS service.
- `Backdoor:IAMUser/BackdoorUser` — a backdoor IAM user was created (or
  an existing user's credentials were modified for persistence).
- `Persistence:IAMUser/BackdoorUser` — persistence mechanism via IAM user
  manipulation.
- `PrivilegeEscalation:IAMUser/AnomalousBehavior` — ML-detected
  privilege-escalation behavior. The model detected API-call patterns
  consistent with an attacker escalating privileges.
- `CredentialAccess:IAMUser/AnomalousBehavior` — suspicious credential
  access (e.g., mass `GetSecretValue` calls, `GetCallerIdentity` probing).
- `Trojan:EC2/SuspiciousFile` — a suspicious file was detected on the EC2
  instance (via GuardDuty Malware Protection). Not yet confirmed malware,
  but high probability.
- `Trojan:EC2/*` (generic Trojan findings with confirmed indicators but
  without active C2 — active C2 escalates to CRITICAL per Step 2).

### Step 4: MEDIUM — suspicious behavioral anomaly (investigate within 24h)

If the finding type is in the MEDIUM list below, output **MEDIUM**. These
are behavioral-anomaly or reconnaissance findings that need investigation
but are not strong compromise indicators. GuardDuty's ML models flagged
unusual activity; the activity MAY be benign (false positive not caught by
Step 1) or MAY be early-stage reconnaissance.

**MEDIUM finding types:**

- `UnauthorizedAccess:IAMUser/ConsoleLoginFromAnomalousLocation` —
  console login from a geo-location unusual for this user. Could be a
  compromised credential or legitimate travel. Investigate by checking
  whether the user recognizes the login location and MFA was used.
- `Recon:EC2/PortSweepUnusual` (from an unknown source, not matching FP-1
  or FP-2) — unusual port sweep from an unrecognized source. Investigate
  the source IP and the target instance's exposure.
- `Recon:IAMUser/UserPermissionsLocations` — unusual permission
  enumeration. Could be legitimate IAM review or attacker mapping the
  account's permission landscape.
- `Discovery:IAMUser/AnomalousBehavior` — ML-detected discovery behavior
  (e.g., unusual `List*` / `Describe*` API call volume).
- `Discovery:EC2/PortSweep` (from an unknown source) — port sweep from
  an EC2 instance in the account. The instance may be compromised and
  performing internal reconnaissance.
- `InitialAccess:IAMUser/AnomalousBehavior` — suspicious initial-access
  pattern.
- `TTP*:*` / `TTPs*:*` findings at GuardDuty severity 5.0-7.99 —
  Tactics/Techniques/Procedures findings in the MEDIUM band.

### Step 5: LOW — reconnaissance, low impact (monitor)

If the finding type is in the LOW list below, output **LOW**. These are
reconnaissance attempts that were blocked or have minimal impact. They do
not indicate a compromise but represent an adversary gathering
information. Add to the monitoring queue; no immediate action needed.

**LOW finding types:**

- `Recon:EC2/PortProbeUnprotectedPort` — port probe against an
  unprotected port (no security-group rule blocking it). The probe
  itself is not an attack, but the port being "unprotected" means the
  security group allows traffic on it — verify the port should be open.
- `Recon:EC2/PortProbeListingPort22` — port probe targeting SSH (port 22).
  Common internet background noise.
- `Recon:EC2/PortSweep` (basic, from external source) — external port
  sweep. Internet background noise unless the source is internal.
- `Recon:IAMUser/MaliciousIPCaller` — API call from a suspicious IP at
  the LOW severity tier. Less certain than the HIGH-severity variant.
- `Trojan:EC2/DGADomainRequest!DNS` (severity < 5.0) — DGA-like domain
  request at low severity. Often a false positive from short-lived CDN
  subdomains, but worth monitoring for patterns.
- `Trojan:EC2/SuspiciousDomainRequest!DNS` (severity < 5.0) — suspicious
  domain request at low severity.

### Step 6: Numeric severity fallback

If the finding type does not match any of the lists above (new or uncommon
finding type), fall back to GuardDuty's numeric severity:

- 8.0 - 10.0 → **HIGH** (do not default to CRITICAL for unknown types —
  CRITICAL requires a finding type in the Step 2 list)
- 5.0 - 7.99 → **MEDIUM**
- 1.0 - 4.99 → **LOW**

Always note in the REASON that the finding type was not in the known
taxonomy and the verdict is based on numeric severity only. This signals
to the SOC analyst that manual review of the finding type is needed.

### Step 7: Context overlays (apply after severity classification)

After determining the base verdict from Steps 1-6, apply these overlays:

**Count-based escalation:** GuardDuty's `service.count` field reflects
how many times the activity was observed in the aggregation window (6
hours for most findings, 5-minute sub-windows for brute-force). The
count threshold for escalation depends on the finding type because
aggregation semantics differ:

| Finding family | Escalate when count ≥ | Rationale |
|---|---|---|
| `*BruteForce` (SSH/RDP) | 100 | 100+ attempts in 6h = ~17/hour; below that is typical internet background SSH noise against exposed instances |
| `Recon:EC2/PortProbe*` | 20 | Port-probe count is unique source-IP/target-port pairs; 20+ means systematic scanning, not incidental probing |
| `*DGADomainRequest*DNS` / `*SuspiciousDomain*DNS` | 15 | DNS count is per-domain; 15+ queries to the same suspicious domain in 6h suggests C2 beaconing, not a one-off misresolve |
| `*:AnomalousBehavior` (ML) | 5 | ML findings fire on statistical outliers; 5+ means the outlier pattern is sustained, not a single API-call burst |
| All other finding types | 30 | General sustained-activity threshold for 6h aggregation (~5 events/hour) |

When the threshold is met, escalate one band: LOW → MEDIUM, MEDIUM →
HIGH. Do not escalate HIGH → CRITICAL based on count alone — CRITICAL
requires a finding type in the Step 2 list.

Count-overlay edge cases moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Step 7 overlay edge cases

**Resource-criticality escalation:** If the affected resource is
production-critical, escalate one band: LOW → MEDIUM, MEDIUM → HIGH.
Detect production-criticality using these concrete signals, checked in
order:

Criticality-signal detail (tags, resource-type heuristics, live lookup) moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Resource-criticality detection signals

Confidence de-escalation nuance moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Confidence-signal de-escalation

## Severity / risk matrix

Full severity/risk matrix moved to references; the compact severity map above remains authoritative.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Severity / risk matrix

## GuardDuty finding-type anatomy

Finding-type anatomy, aggregation semantics, detection-confidence hierarchy, additionalInfo deep fields, and ECS/EKS edge cases moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § GuardDuty finding-type anatomy

## False-positive detection — quick-reference decision tree

```
Is the source an authorized scanner / LB health-checker?
├── YES → LIKELY_FALSE_POSITIVE (FP-1 / FP-2)
└── NO → Is it a DNS finding on a known-safe domain?
    ├── YES → LIKELY_FALSE_POSITIVE (FP-3)
    └── NO → Is it Tor traffic on a public-facing service?
        ├── YES → LIKELY_FALSE_POSITIVE (FP-4)
        └── NO → Is the caller an AWS service-linked role in normal scope?
            ├── YES → LIKELY_FALSE_POSITIVE (FP-5)
            └── NO → Is there a documented change window?
                ├── YES → LIKELY_FALSE_POSITIVE (FP-6)
                └── NO → Proceed to severity classification (Step 2+)
```

## Output format (per finding)

```text
FINDING: <finding-name>
VERDICT: CRITICAL | HIGH | MEDIUM | LOW | LIKELY_FALSE_POSITIVE
REASON: <1-2 sentences citing the classification step, the finding type, and the context that determined the verdict>
REMEDIATION: <specific action, or "Archive — likely false positive (<FP pattern>)" for FP>
```

The `<finding-name>` is the label or identifier supplied with the finding
input (e.g., the `Finding name` field). If no name is supplied, use the
finding `type` string.

### Multi-finding aggregation example

Multi-finding aggregation example moved to references.
→ [references/worked-examples.md](references/worked-examples.md) § Multi-finding aggregation example

## NEVER (anti-patterns)

- NEVER auto-archive an `Impact:*` finding without verifying the
  resource is not compromised, even if the source IP looks internal or
  the activity "seems expected." Crypto-mining and DDoS-participant
  findings are CRITICAL — an attacker may have compromised an internal
  instance and is using it as a launching point. Archiving without
  verification destroys evidence and extends the compromise window.

- NEVER classify `UnauthorizedAccess:EC2/InstanceCredentialExfiltration.OutsideAWS`
  as anything other than CRITICAL. This finding means EC2 instance-profile
  credentials were stolen and are being used from outside AWS — the
  attacker can access any resource the instance role can access. Treating
  this as MEDIUM because the numeric severity is "only 8.0" misses that
  the blast radius is the entire permission boundary of the instance role.

- NEVER treat Tor traffic to a private/internal service as a false
  positive. FP-4 applies ONLY to public-facing services designed for
  anonymous access. Tor traffic targeting an RDS instance, an internal
  API, or an EC2 instance with no public-facing purpose is a strong
  reconnaissance or compromise indicator — classify as HIGH.

- NEVER suppress a finding type globally without understanding the
  blast radius. A suppression filter on `Recon:EC2/PortProbeUnprotectedPort`
  from one scanner IP is safe; a suppression filter on ALL
  `Recon:EC2/PortProbeUnprotectedPort` findings hides every port-probe
  across the entire account, including probes from genuinely malicious
  IPs. Always scope suppression filters to specific IPs, accounts, or
  resource ARNs.

- NEVER assume a LOW severity finding can be ignored.
  `Recon:EC2/PortProbeUnprotectedPort` at severity 2.0 seems harmless,
  but the "unprotected" in the finding type means the security group
  ALLOWS traffic on the probed port — the port is reachable. If the port
  is 3389 (RDP) or 22 (SSH), a follow-up brute-force finding is likely.
  Investigate WHY the port is unprotected.

- NEVER classify a behavioral-anomaly finding
  (`*:IAMUser/AnomalousBehavior`, `*:EC2/AnomalousBehavior`) as
  LIKELY_FALSE_POSITIVE without matching it to FP-6 (documented change
  window). ML-based findings have false-positive rates, but the skill's
  FP patterns require specific evidence — "it's probably nothing" is
  not a valid false-positive justification.

- NEVER recommend terminating a compromised EC2 instance as the first
  remediation step. Termination destroys volatile evidence (RAM contents,
  running processes, network connections). The correct order is:
  isolate (security-group quarantine) → capture forensic state (EBS
  snapshot, memory dump if possible) → investigate → then terminate or
  rebuild.

- NEVER downgrade a finding's verdict based solely on GuardDuty's
  confidence score. Low confidence on a CRITICAL finding type (crypto
  mining, credential exfiltration) still warrants CRITICAL response —
  the cost of missing a real compromise far exceeds the cost of a
  false-alarm investigation. Note the low confidence in the REASON
  field but keep the verdict. For example, an
  `Impact:EC2/CryptocurrencyClient` finding at confidence 0.3 is still
  CRITICAL — the confidence reflects the ML model's certainty, not the
  operational urgency. A missed crypto-miner at 0.3 confidence costs
  more than a false-alarm investigation at 0.3 confidence.

- NEVER rely on the finding `title` for classification — always use the
  finding `type` field. The title is human-readable and may use different
  wording between GuardDuty versions; the type is the stable machine
  identifier that maps to the threat taxonomy.

- NEVER apply count-based escalation to a LIKELY_FALSE_POSITIVE verdict.
  A finding from an authorized scanner with count=500 is still a false
  positive — the scanner ran a comprehensive scan. Escalation overlays
  apply only to severity-classified findings (Step 2-6), not to
  false-positive overrides (Step 1).

- NEVER create a suppression filter scoped to a finding TYPE without an
  IP/resource constraint. A filter that auto-archives ALL
  `UnauthorizedAccess:EC2/SSHBruteForce` findings suppresses the next
  real attack alongside the noise. Suppression filters must always
  include a `sourceIp` or `resource.instanceDetails.instanceId`
  criterion — never just the finding type. This is the single most
  dangerous GuardDuty misconfiguration: a broad filter silently disables
  threat detection for an entire attack class. Review all auto-archive
  filters quarterly and remove any that are broader than a specific IP
  or resource ARN.

- NEVER allow suppression filters to accumulate without periodic audit.
  Suppression filters are additive — each `create-filter` call with
  `ARCHIVE` action adds a permanent auto-archive rule. Over months,
  filters stack up and interact: a filter for scanner IP A on
  `PortProbeUnprotectedPort` plus a filter for finding type
  `TorIPCaller` plus a stale filter from a decommissioned pentest can
  collectively blind detection across multiple threat categories. Audit
  quarterly with `aws guardduty list-filters --detector-id <id>` and
  delete any filter whose IP/CIDR no longer corresponds to an active,
  authorized source. If the filter count exceeds ~15 active ARCHIVE
  filters on a single detector, consolidate or remove — high filter
  counts correlate strongly with missed detections in post-incident
  reviews.

- NEVER treat GuardDuty's `severity` field as the triage verdict without
  applying the threat-category overlay (Steps 2-3). The numeric severity
  reflects the threat family's baseline, not the operational urgency.
  `Impact:EC2/CryptocurrencyClient` at severity 8.0 is CRITICAL (active
  compromise), not HIGH. `UnauthorizedAccess:EC2/SSHBruteForce` at
  severity 7.0 is HIGH (brute-force success leads to compromise), not
  MEDIUM. Parroting the numeric band without escalation misses the
  entire purpose of triage.

- NEVER treat a low `confidence` score on an ML-based HIGH finding
  (`PrivilegeEscalation:IAMUser/AnomalousBehavior`,
  `CredentialAccess:IAMUser/AnomalousBehavior`,
  `Discovery:IAMUser/AnomalousBehavior`) as permission to downgrade or
  auto-archive. GuardDuty's confidence field reflects the ML model's
  statistical certainty, not the operational risk. A
  `PrivilegeEscalation:IAMUser/AnomalousBehavior` at confidence 0.4
  still means the model detected privilege-escalation API-call patterns
  — the 0.4 means "moderately confident this is anomalous," not
  "probably safe." The correct response is to investigate the specific
  API calls (check CloudTrail for the exact `AssumeRole`,
  `AttachRolePolicy`, or `PutUserPolicy` calls that triggered the
  finding) and let the evidence — not the confidence number — determine
  the verdict. Conversely, do not treat a high-confidence ML finding as
  confirmed compromise without evidence — confidence 0.9 on
  `ConsoleLoginFromAnomalousLocation` still requires checking whether
  the user recognizes the login location and whether MFA was used.

## Pre-flight safety checks (run before any remediation CLI)

- **Confirm the resource identity.** Before isolating an EC2 instance or
  revoking credentials, verify the instance ID / IAM principal ARN matches
  the finding. GuardDuty findings reference specific resource IDs — a
  typo or stale finding can cause remediation on the wrong resource.
  Run: `aws ec2 describe-instances --instance-ids <id>` or
  `aws iam get-role --role-name <name>` to confirm.

Forensic-capture, blast-radius, flow-log, and suppression-scope check commands moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Pre-flight safety checks — command detail

## Remediation guidance

Per-verdict remediation command sequences moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Remediation guidance — per-verdict commands

## Recent AWS features (2024-2026)

2024-2026 feature notes moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Recent AWS features (2024-2026)

## References

Legacy reference links moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Additional AWS reference links

## Security Hub integration and ASFF severity mapping

Security Hub ASFF mapping and EventBridge routing detail moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Security Hub integration and ASFF severity mapping

## Section taxonomy (CloudOps auditor pattern)

Section taxonomy moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Section taxonomy

## References (load on demand)

Consult these only when the corresponding topic comes up:

- [references/false-positive-patterns.md](references/false-positive-patterns.md) — the quick FP check and the detailed FP-1..FP-6 pattern definitions (moved from Step 1)
- [references/error-handling.md](references/error-handling.md) — malformed-finding-JSON handling, stale findings, and naming-convention validation (moved from Step 0)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight safety-check commands and per-verdict remediation command sequences
- [references/worked-examples.md](references/worked-examples.md) — the multi-finding aggregation example (moved from § Output format)
- [references/advanced-patterns.md](references/advanced-patterns.md) — full mindset framing, band rationales, Step 7 overlay detail, finding-type anatomy, severity/risk matrix, Security Hub mapping, and recent AWS features
## Domain

AWS CloudOps / Security Operations & Threat Detection.

## AWS documentation

- **Amazon GuardDuty User Guide** — https://docs.aws.amazon.com/guardduty/latest/ug/what-is-guardduty.html
- **GuardDuty Security** — https://docs.aws.amazon.com/guardduty/latest/ug/security.html
- **GuardDuty API Reference** — https://docs.aws.amazon.com/guardduty/latest/APIReference/
- **GuardDuty CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/guardduty/
- **Runtime Monitoring for ECS/EKS** — https://docs.aws.amazon.com/guardduty/latest/ug/runtime-monitoring.html
- **GuardDuty finding types** — https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-active.html
