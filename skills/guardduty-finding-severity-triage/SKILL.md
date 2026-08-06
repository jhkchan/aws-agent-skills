---
name: guardduty-finding-severity-triage
description: >-
  Classifies Amazon GuardDuty findings into a context-aware triage severity
  (CRITICAL | HIGH | MEDIUM | LOW | LIKELY_FALSE_POSITIVE) by overlaying
  finding-type threat taxonomy, false-positive signals, aggregation counts,
  and resource criticality on top of GuardDuty's numeric severity. Detects
  authorized-scanner port sweeps, Tor traffic to public services, known-safe
  DNS domains, and AWS service-linked role activity as false-positives.
  Provides per-verdict incident-response remediation steps. Use when
  triaging GuardDuty findings (JSON or structured text) for SOC
  prioritization, false-positive filtering, or escalation decisions.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf). No AWS
  CLI required for offline finding classification — the skill reasons over
  provided finding JSON or structured text. Live-account triage uses
  aws guardduty list-findings / get-findings and aws guardduty archive-finders
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - GuardDuty
  - finding severity
  - threat triage
  - false positive
  - PortSweepUnusual
  - TorIPCaller
  - CryptocurrencyClient
  - SSHBruteForce
  - MaliciousIPCaller
  - credential exfiltration
  - suppression filter
tags: [guardduty, security, threat-detection, triage, false-positive, incident-response, mitre-attack]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Security
  verdict_shape: "CRITICAL | HIGH | MEDIUM | LOW | LIKELY_FALSE_POSITIVE"
  when_to_use: >-
    Triage a GuardDuty finding (JSON or structured text) to determine its
    real-world response priority, check whether a finding is a likely
    false-positive (authorized scanner, known-safe DNS, public service Tor
    traffic), decide which findings to escalate to incident response,
    prioritize findings for a SOC queue, or determine whether to archive or
    suppress a recurring finding pattern.
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

GuardDuty assigns each finding a numeric severity from 1.0 to 10.0 and maps
that to three bands: LOW (1.0-4.99), MEDIUM (5.0-7.99), HIGH (8.0-10.0).
That mapping is a starting point, not a verdict. The numeric severity
reflects the *threat category* GuardDuty detected — it does not encode
operational context that determines whether the finding represents a genuine
threat to THIS account at THIS time.

A `Recon:EC2/PortSweepUnusual` finding at severity 6.0 from a known Nessus
scanner is a false positive — the port sweep is authorized. A
`Impact:EC2/CryptocurrencyClient` at severity 8.0 on a production database
instance is not merely HIGH — it is CRITICAL, because crypto mining confirms
active compromise and every minute of delay increases blast radius. A
`Trojan:EC2/DGADomainRequest!DNS` at severity 5.0 resolving to
`cloudfront.net` is noise — the domain is a CDN, not a DGA.

The triage layer this skill provides sits BETWEEN GuardDuty's raw severity
and the SOC queue. It overlays four dimensions that GuardDuty does not:

1. **False-positive context** — Is the activity expected (authorized
   scanner, public service, known-safe domain, AWS service activity)?
2. **Threat-category escalation** — Some finding types always warrant a
   higher verdict than their numeric severity suggests (credential
   exfiltration, crypto mining, confirmed C2).
3. **Aggregation and persistence** — A finding with `count` > 50 is
   sustained activity, not a one-off; escalate one band.
4. **Resource criticality** — The same finding on a production data store
   is more urgent than on a sandbox instance.

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

**Malformed finding JSON:** If the finding JSON is unparseable (truncated
`get-findings` output, missing closing braces, `null` fields where strings
are expected), output VERDICT: ERROR with REASON "finding JSON unparseable
— re-fetch the finding." Do NOT guess the finding type from a fragment —
a misread type leads to wrong severity classification. Specific edge
cases to handle:

- **`severity` as a string** (e.g., `"severity": "8.0"` instead of
  `"severity": 8.0`): some API proxies and export pipelines serialize
  numbers as strings. Parse it as a float before classification; do not
  error.
- **`resource` present but `resourceType` missing or null**: the finding
  has a resource block but no type identifier. Try to infer the type
  from the finding-type string's `ResourceType` segment (between `:` and
  `/`). If neither is available, output ERROR.
- **Finding type truncated** (e.g., `Impact:EC2/Crypto` instead of
  `Impact:EC2/CryptocurrencyClient`): do not pattern-match a partial
  type. Output ERROR — a truncated type means the finding was corrupted
  in transit.
- **`service.eventFirstSeen` / `eventLastSeen` missing**: skip the
  staleness check (Step 0) and proceed with classification. Note in
  REASON: "timestamps unavailable; staleness not assessed."
- **AWS partition mismatch** (GovCloud `us-gov`, China `cn-`): finding
  types are the same across partitions, but threat-intel IP lists and
  trusted-IP sets are partition-specific. If the finding is from GovCloud
  or China partition (check the finding ARN or account ID region prefix),
  note that FP-1/FP-2 IP-range checks may not apply — GovCloud uses
  different ELB health-checker IP ranges.

**Stale findings:** If `eventLastSeen` is more than 30 days in the past,
the finding is historical. GuardDuty retains findings for 90 days. Old
findings may reference resources that no longer exist (terminated
instances, deleted IAM users). Note the staleness in the REASON field
and check resource existence before recommending remediation:
`aws ec2 describe-instances --instance-ids <id>` or
`aws iam get-user --user-name <name>`.

Additionally, verify the finding type matches the GuardDuty naming
convention: `ThreatPurpose:ResourceType/ThreatFamilyName[.Variant][!DetectionMethod]`.
If the type does not parse (e.g., a raw string without the colon/slash
delimiter), flag it as ERROR — a malformed finding type means the detector
output is corrupt or the finding was hand-edited.

### Step 1: False-positive override (evaluate FIRST — highest priority)

Before applying any severity classification, check whether the finding
matches a known false-positive pattern. False-positive context overrides
numeric severity — a severity-8.0 finding from an authorized scanner is
still a false positive.

**Quick FP check** (from the Triage in 30 seconds section): Is the source
an authorized scanner or LB health-checker? → FP-1/FP-2. Is it a DNS
finding on a known-safe domain? → FP-3. Is it Tor traffic on a public
service? → FP-4. Is the caller an AWS service-linked role in normal
scope? → FP-5. Is there a documented change window? → FP-6. If none
match, proceed to Step 2.

The detailed pattern definitions below are for complex or ambiguous cases
where the quick check is inconclusive. Evaluate these patterns in order:

**FP-1: Authorized security scanner.**

Applies to: `Recon:EC2/PortSweepUnusual`, `Recon:EC2/PortProbeUnprotectedPort`,
`Recon:EC2/PortSweep`, `Discovery:EC2/PortSweep`.

All of the following must be true:
- The source IP or instance is identified as an authorized security
  scanner (Nessus, Qualys, Rapid7, internal pentest tool). Source signals:
  the instance is tagged or named with a scanner identifier (e.g.,
  `security-scanner-nessus`, `pentest-kali`), the source IP is within an
  approved pentest CIDR range documented in the account's security runbook,
  or the finding's `additionalInfo` field contains a scanner signature.
- The swept/probed ports are consistent with a vulnerability scan (common
  scan ports: 22, 80, 443, 445, 3389, 1521, 3306, 5432, 6379, 8080, 8443,
  full range 1-65535 for comprehensive scans).

Verdict: **LIKELY_FALSE_POSITIVE**.
Remediation: Archive the finding. Add the scanner's source IP range to
GuardDuty's Trusted IP list (`aws guardduty update-ip-set`) to suppress
future findings of this type from that source.

**FP-2: Load-balancer health-check port sweep.**

Applies to: `Recon:EC2/PortSweepUnusual`, `Discovery:EC2/PortSweep`.

True when the source is an AWS-managed ELB/NLB health checker and the
ports swept match the configured health-check ports. AWS NLB cross-zone
health checks can trigger port-sweep findings because the health checker
probes instances across subnets. Source signals: the source IP is within
AWS ELB health-check IP ranges (published in the AWS IP ranges JSON under
`ELASTICLOADBALANCING`), and the finding's `action.portSweepAction` targets
only the health-check port(s).

Verdict: **LIKELY_FALSE_POSITIVE**.

**FP-3: Known-safe DNS domain.**

Applies to: `Trojan:EC2/DGADomainRequest!DNS`, `Trojan:EC2/SuspiciousDomainRequest!DNS`,
`Trojan:EC2/PhishingDomain!DNS`, `Trojan:EC2/PhishingDomainRequest!DNS`.

True when the queried domain is known-safe:
- The domain resolves to or is a subdomain of a major CDN or SaaS platform
  (`cloudfront.net`, `akamai.net`, `fastly.net`, `cloudflare.com`,
  `amazonaws.com`, `googleusercontent.com`).
- The domain is on an organizational allow-list (managed in the security
  team's threat-intel feed).
- The domain is an AWS managed domain (`aws.amazon.com`, `amazonaws.com`,
  `awsstatic.com`, `media-amazon.com`).

**Important:** This FP pattern applies to DNS-request-based findings where
the DGA/suspicious classification is based on domain-name entropy heuristics.
It does NOT apply to findings where the domain is a confirmed phishing or
C2 domain in threat-intel feeds — if the domain appears in a reputable
threat-intel feed, escalate regardless of CDN resemblance.

Verdict: **LIKELY_FALSE_POSITIVE**.

**FP-4: Expected Tor traffic on public-facing service.**

Applies to: `UnauthorizedAccess:EC2/TorIPCaller`, `UnauthorizedAccess:EC2/TorClient`.

True when the target resource is a public-facing service designed for
anonymous access:
- An Application Load Balancer, API Gateway, or CloudFront distribution
  serving public content where anonymous/Tor access is expected (e.g., a
  whistleblower portal, anonymous tip line, public API, onion-service
  mirror).
- The service has no authentication requirement (public endpoint) and
  Tor traffic does not violate the application's security posture.

**Important:** If the Tor traffic targets a private/internal service (an
RDS instance, an internal API, an EC2 instance with no public-facing
purpose), this FP does NOT apply — escalate to HIGH. Tor traffic to an
internal service is a strong indicator of reconnaissance or compromise.

Verdict: **LIKELY_FALSE_POSITIVE**.

**FP-5: AWS service-linked role activity.**

Applies to: `Discovery:IAMUser/*`, `Recon:IAMUser/*`.

True when the caller identity is an AWS service-linked role or
AWS-internal service principal:
- The caller ARN matches `arn:aws:iam::*:role/aws-service-role/*` or
  `AWSServiceRoleFor*`.
- The API call was made by an AWS service (e.g., AWS Config running a
  configuration snapshot, Security Hub running an aggregation, AWS
  Organizations listing accounts).

These roles are managed by AWS and their API activity is expected.
However, if the service-linked role is performing actions outside its
normal scope (e.g., an `AWSServiceRoleForConfig` calling `iam:CreateUser`),
that is NOT a false positive — it indicates a compromised service role or
an attack using the role's credentials. Escalate to CRITICAL.

Verdict: **LIKELY_FALSE_POSITIVE** (only when activity is within the
service role's expected scope).

**FP-6: Documented change-window behavioral anomaly.**

Applies to: `*:IAMUser/AnomalousBehavior`, `*:EC2/AnomalousBehavior`,
`UnauthorizedAccess:IAMUser/ConsoleLoginFromAnomalousLocation`.

True when the finding's timestamp falls within a documented change window
(migration, DR drill, scheduled maintenance) AND the anomalous behavior is
consistent with the planned activity:
- A CloudTrail event showing console login from a new country during a
  documented infrastructure migration.
- Unusual API call patterns during a DR failover test.
- Mass IAM permission changes during an organizational restructuring.

The change window must be documented (a change-management ticket, a DR
runbook entry, a migration plan) — not retroactively justified. If the
finding predates the change ticket, the behavior may be the cause of the
change request, not a result of it.

Verdict: **LIKELY_FALSE_POSITIVE** (only when documented change window
is confirmed).

### Step 2: CRITICAL — active compromise (immediate IR required)

If the finding type is in the active-compromise list below, output
**CRITICAL** regardless of the numeric severity. These finding types
indicate a confirmed or near-confirmed active threat — the resource is
compromised and is being used for malicious purposes. GuardDuty may
assign these severity 8.0 (HIGH band), but the triage severity is CRITICAL
because the finding represents an ongoing incident, not a risk to
investigate.

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

**Severity escalation to CRITICAL (from HIGH numeric):**
Even if GuardDuty assigns these a severity below 8.0, the triage verdict is
CRITICAL. The numeric severity reflects the threat family, not the
operational urgency. Crypto mining, credential exfiltration, and confirmed
C2 are all immediate-IR scenarios where the response time directly
determines blast radius.

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

**Escalation cap for unknown finding types:** If the base verdict came
from Step 6 (numeric fallback, unknown finding type), count-based
escalation caps at MEDIUM — do not escalate an unknown finding type
above MEDIUM via count alone. The count threshold tells you the
activity is sustained, but without knowing the threat family, escalating
to HIGH could over-prioritize a benign high-volume pattern. Note in
REASON: "count threshold met but finding type not in known taxonomy —
capped at MEDIUM pending manual review."

**Missing or null count:** If `service.count` is absent, null, or 0
(can happen with malformed findings, API-export truncation, or findings
from third-party integrations via `aws guardduty import-findings`), do
NOT apply count-based escalation. Instead, check `eventLastSeen` — if
it is within the last 6 hours, treat the activity as potentially
ongoing and note in REASON: "count unavailable; assuming recent
activity based on eventLastSeen." If `eventLastSeen` is also absent,
skip the count overlay entirely and rely on the base verdict.

**Count exemption for false-positive sources:** Do not apply count
escalation to findings where the source has already been identified as
an authorized scanner (FP-1) or LB health-checker (FP-2). A Nessus
scanner running a full sweep generates count=500+ on PortSweepUnusual —
that is expected scanner volume, not sustained attack activity.

**Resource-criticality escalation:** If the affected resource is
production-critical, escalate one band: LOW → MEDIUM, MEDIUM → HIGH.
Detect production-criticality using these concrete signals, checked in
order:

1. **Resource tags in the finding JSON.** GuardDuty includes resource
   tags in `resource.instanceDetails.tags`,
   `resource.rdsDbInstanceDetails.tags`, and
   `resource.eksClusterDetails.tags` as a list of `{key, value}` pairs.
   Treat as production-critical if any tag matches:
   - `Environment` / `env` / `environment` = `prod`, `production`,
     `live`, `critical`
   - `Criticality` / `Priority` / `Tier` = `tier-0`, `tier-1`,
     `critical`, `high`, `mission-critical`
   - `DataClassification` / `Sensitivity` = `confidential`,
     `restricted`, `pii`, `phi`, `secret`

2. **Resource type heuristic.** Some resource types are inherently
   high-blast-radius regardless of tags:
   - `RDSDBInstance` / `RDSDBCluster` — production data store; a
     compromise means data breach.
   - IAM principal with `AdministratorAccess` or a policy granting
     `*:*` on `*` — compromise means full account takeover.
     Live-account check:
     `aws iam list-attached-role-policies --role-name <name>` and
     `aws iam list-inline-role-policies --role-name <name>`.
   - S3 bucket with `sensitive`, `prod`, `backup`, or `audit` in the
     bucket name or with a `DataClassification` tag.

3. **Live-account tag lookup** (when the finding JSON omits tags). Use
   AWS Resource Groups Tagging API to check the resource's tags:
   `aws resourcegroupstaggingapi get-resources --tag-filters
   Key=Environment,Values=prod --resource-type-filters
   ec2:instance,rds:db`. If the resource ARN from the finding appears in
   the results, it carries a production tag.

If none of these signals are available (no tags in the finding, no live
account access), skip this overlay and note in REASON: "resource
criticality unknown — no tags available."

**Confidence-signal de-escalation:** If the finding's confidence is LOW
(GuardDuty reports a `confidence` value below 0.5, or the finding type
is ML-based with known high false-positive rates), AND no other context
confirms the threat, consider noting reduced confidence in the REASON
field. Do not auto-de-escalate based on confidence alone — low confidence
on a CRITICAL finding type (crypto mining) still warrants CRITICAL
response because the cost of missing a real threat exceeds the cost of
a false alarm.

## Severity / risk matrix

| Finding type | GD severity | Triage verdict | IR urgency |
|---|---|---|---|
| `Impact:EC2/CryptocurrencyClient` | 8.0+ | CRITICAL | Immediate (isolate) |
| `Impact:EC2/BitcoinTool.B` | 8.0+ | CRITICAL | Immediate (isolate) |
| `Impact:EC2/AbusedThroughDDoS` | 8.0+ | CRITICAL | Immediate (isolate) |
| `Impact:EC2/HostLost` | 8.0+ | CRITICAL | Immediate (isolate) |
| `Exfiltration:*` | 7.0+ | CRITICAL | Immediate (contain) |
| `UnauthorizedAccess:EC2/InstanceCredentialExfiltration.OutsideAWS` | 8.0+ | CRITICAL | Immediate (revoke creds) |
| `Backdoor:EC2/CC*` | 8.0+ | CRITICAL | Immediate (isolate) |
| `DefenseEvasion:EC2/AssumedRoleAccessKeyDeleteOrDisable` | 8.0+ | CRITICAL | Immediate (IR) |
| `UnauthorizedAccess:IAMUser/MaliciousIPCaller` | 8.0+ | HIGH | < 4 hours |
| `UnauthorizedAccess:EC2/SSHBruteForce` | ~7.0 | HIGH | < 4 hours |
| `UnauthorizedAccess:EC2/RDPBruteForce` | ~7.0 | HIGH | < 4 hours |
| `Backdoor:IAMUser/BackdoorUser` | 8.0+ | HIGH | < 4 hours |
| `PrivilegeEscalation:IAMUser/AnomalousBehavior` | 7.0+ | HIGH | < 4 hours |
| `Trojan:EC2/SuspiciousFile` | 7.0+ | HIGH | < 4 hours |
| `UnauthorizedAccess:IAMUser/ConsoleLoginFromAnomalousLocation` | ~5.0 | MEDIUM | < 24 hours |
| `Recon:EC2/PortSweepUnusual` (unknown source) | ~6.0 | MEDIUM | < 24 hours |
| `Recon:IAMUser/UserPermissionsLocations` | ~5.0 | MEDIUM | < 24 hours |
| `Discovery:IAMUser/AnomalousBehavior` | ~5.0 | MEDIUM | < 24 hours |
| `Recon:EC2/PortProbeUnprotectedPort` | ~2.0 | LOW | Monitor |
| `Recon:EC2/PortProbeListingPort22` | ~2.0 | LOW | Monitor |
| `Trojan:EC2/DGADomainRequest!DNS` (< 5.0) | ~2.0 | LOW | Monitor |
| `Recon:EC2/PortSweepUnusual` (from scanner) | any | LIKELY_FALSE_POSITIVE | Archive |
| `UnauthorizedAccess:EC2/TorIPCaller` (on public ALB) | ~5.0 | LIKELY_FALSE_POSITIVE | Archive |
| `Trojan:EC2/DGADomainRequest!DNS` (CDN domain) | ~5.0 | LIKELY_FALSE_POSITIVE | Archive |
| `Discovery:IAMUser/*` (AWS service role) | any | LIKELY_FALSE_POSITIVE | Archive |

## GuardDuty finding-type anatomy

Understanding the finding-type string is essential for accurate triage.
The format is:

```
ThreatPurpose:ResourceType/ThreatFamilyName[.Variant][!DetectionMethod]
```

- **ThreatPurpose** — the high-level category, mapped to MITRE ATT&CK
  tactics: `Recon` (Reconnaissance), `Discovery` (Discovery),
  `UnauthorizedAccess` (Initial Access), `Impact` (Impact),
  `Backdoor` (Persistence/C2), `Trojan` (Execution/Malware),
  `Persistence` (Persistence), `PrivilegeEscalation` (Privilege Escalation),
  `DefenseEvasion` (Defense Evasion), `Exfiltration` (Exfiltration),
  `CredentialAccess` (Credential Access).

- **ResourceType** — `EC2`, `IAMUser`, `S3`, `EKSCluster`, `Container`,
  `RDSDBInstance`, `RDSDBUser`. This determines which resource details
  the finding carries.

- **ThreatFamilyName** — the specific threat family (e.g.,
  `CryptocurrencyClient`, `PortSweepUnusual`, `MaliciousIPCaller`).

- **.Variant** (optional) — a sub-variant (e.g., `.OutsideAWS`,
  `.Custom`, `.B`). Variants refine the threat — `.OutsideAWS` on a
  credential-exfiltration finding means the credentials are being used
  outside the AWS network, which is a stronger indicator than in-network
  use.

- **!DetectionMethod** (optional) — how the threat was detected:
  `!DNS` (via DNS logs / Route 53 Resolver), `!SSH` (via SSH connection
  analysis), `!VPC` (via VPC Flow Logs). DNS-based findings have higher
  false-positive rates because domain-name heuristics (DGA detection,
  suspicious-domain matching) produce more noise than network-connection
  analysis. When a finding carries `!DNS`, apply higher scrutiny to the
  FP-3 (known-safe DNS domain) check — the domain heuristic is the
  detection signal itself, and CDN subdomains with high-entropy names
  frequently trigger DGA false positives.

### Aggregation windows and count semantics

GuardDuty aggregates repeated instances of the same finding type against
the same resource into a single finding with a `count` field. The
aggregation window depends on the finding type:

- **Most findings**: 6-hour aggregation window. The `count` field reflects
  how many times the activity was observed in the last 6 hours. A count
  of 50+ on a 6-hour window means sustained activity (roughly 8+ events
  per hour).
- **Brute-force findings** (`SSHBruteForce`, `RDPBruteForce`): shorter
  aggregation (5-minute windows within the 6-hour span). A count of 240
  on SSH brute-force means 240 failed attempts — the attacker is
  aggressively attempting credential compromise.
- **Port probe findings**: aggregated by unique source-IP/target-port
  pairs. A count of 3 means 3 distinct probes, not 3 packets.

The `count` field resets when the activity stops for one full aggregation
window. A finding with `count: 1` and `eventLastSeen` more than 6 hours
ago is stale — the activity has stopped. Check `eventFirstSeen` and
`eventLastSeen` to determine whether the threat is ongoing.

### Detection source confidence hierarchy

Not all GuardDuty detections have equal reliability. The detection source
affects the false-positive probability:

1. **Malware Protection (file hash scan)** — highest confidence. A file
   hash match against threat-intel databases is near-deterministic. If
   `Trojan:EC2/SuspiciousFile` fires with a confirmed hash, treat as
   confirmed malware.
2. **Threat-intel IP match** — high confidence. IP addresses on
   GuardDuty's curated threat lists (or your custom list) are
   corroborated by multiple threat-intel feeds.
3. **Network-connection analysis** (`!SSH`, `!VPC`) — medium-high
   confidence. Network behavior is harder to spoof than DNS.
4. **DNS-request heuristics** (`!DNS`) — medium confidence. DGA
   detection and suspicious-domain matching use entropy and reputation
   scoring, which produces more false positives (see FP-3).
5. **ML behavioral anomalies** (`AnomalousBehavior`) — medium-low
   confidence. Machine-learning models detect statistical outliers, but
   outliers include legitimate unusual activity (new admin, new
   workload, DR failover). These findings ALWAYS require human
   context-checking before action.

### `service.additionalInfo` deep fields (finding-specific evidence)

The `service.additionalInfo` field in the finding JSON carries
finding-type-specific metadata that is critical for accurate triage but
frequently overlooked because it is a nested JSON string, not a
top-level field. Parse it to extract:

- **Crypto-mining findings** (`Impact:EC2/CryptocurrencyClient`):
  `processPath` (e.g., `/tmp/xmrig`), `processName`,
  `processCommandLine` — confirms the mining process identity. A
  `processPath` in `/tmp/`, `/dev/shm/`, or a user's home directory on
  a production instance is a confirmed compromise signal.
- **Brute-force findings** (`*SSHBruteForce`, `*RDPBruteForce`):
  `loginAttempts` — the actual number of observed login attempts,
  which may differ from the aggregated `count`. Use this for the
  count-based escalation check (Step 7) instead of `service.count`
  when available — it is more precise.
- **C2 findings** (`Backdoor:EC2/CC*`): `destinationDomain`,
  `destinationAddress`, `sampleTime` — identifies the C2 server.
  Cross-reference `destinationDomain` against threat-intel feeds; if
  it appears in a reputable feed, note the feed name in the REASON.
- **Credential exfiltration**
  (`InstanceCredentialExfiltration.OutsideAWS`):
  `accessKeyId` — the specific stolen access key. Use this to
  immediately check what the key has been doing:
  `aws cloudtrail lookup-events --lookup-attributes
  AttributeKey=AccessKeyId,AttributeValue=<key-id>`.
- **DNS findings** (`*DGADomainRequest!DNS`,
  `*SuspiciousDomainRequest!DNS`): `domainName`,
  `domainLookbackPeriod` — the queried domain and the detection
  window. Short-lived domains (< 24h old in WHOIS) that triggered the
  finding are higher-risk than aged domains.

### ECS/EKS-specific triage edge cases

Container findings (`UnauthorizedAccess:EKS/MaliciousIPCaller`,
`Execution:EKS/MaliciousIPCaller`, `PrivilegeEscalation:EKS/*`) require
different triage than EC2 findings:

- **ECS tasks are ephemeral.** A Fargate task may have been terminated
  and replaced by the time you triage. Check
  `aws ecs describe-tasks --cluster <name> --tasks <task-id>` — if the
  task is already stopped, the threat surface has moved to the new task
  the scheduler launched. The fix is updating the task definition (image
  scan, IAM role tightening), not isolating a dead task.
- **EKS pods share a node.** A compromised pod on a shared EC2 node can
  escalate to node-level access via container escape. For EKS findings,
  check `aws eks describe-nodegroup --cluster-name <name>
  --nodegroup-name <ng>` to identify the underlying EC2 instances — if
  pod-to-node escalation is suspected (check for
  `PrivilegeEscalation:EKS/*` findings on the same cluster), isolate
  the node, not just the pod.
- **Service-linked role for ECS/Fargate.** ECS tasks run under a task
  execution role and a task role. A compromised task role has the
  permissions of that specific role — check its policy scope before
  panicking. A task role with only `s3:GetObject` on a single bucket is
  low blast radius; a task role with `s3:*` on `*` is critical.

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

When triaging multiple findings for the same resource, the resource-level
verdict is the **worst** verdict across all findings:

```text
FINDING: Impact:EC2/CryptocurrencyClient!SSH
VERDICT: CRITICAL
REASON: Step 2 (active compromise) — confirmed crypto-mining client on EC2 instance i-0abc123. Numeric severity 8.0 escalated to CRITICAL because crypto mining confirms active compromise requiring immediate IR.
REMEDIATION: Isolate the instance immediately (Step: CRITICAL IR). Capture forensic state (EBS snapshot, memory dump) then quarantine the security group. Revoke the instance-profile credentials. Do NOT terminate — terminated instances lose volatile memory evidence.

FINDING: Recon:EC2/PortProbeUnprotectedPort
VERDICT: LOW
REASON: Step 5 (reconnaissance) — external port probe on port 3389. Internet background noise; no indication of successful access.
REMEDIATION: Monitor. Verify port 3389 should be open in the security group — if not needed, remove the inbound rule.

RESOURCE: i-0abc123
WORST VERDICT: CRITICAL (from CryptocurrencyClient finding)
```

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

- **Capture forensic state before containment.** For CRITICAL findings:
  - EBS snapshot: `aws ec2 create-snapshot --volume-id <vol-id>
    --description "GD-forensic-<finding-id>" --tag-specifications
    'ResourceType=snapshot,Tags=[{Key=Incident,Value=<id>}]'`
  - Security-group quarantine: create a quarantine SG with no inbound
    rules, then `aws ec2 modify-instance-attribute --instance-id <id>
    --groups <quarantine-sg-id>`. This preserves the instance for
    forensics while cutting network access.

- **Understand the credential blast radius before revoking.** For
  credential-exfiltration findings, do not just list attached policies —
  simulate the principal's effective permissions to account for trust
  policies, permission boundaries, and SCPs that listing misses:
  ```bash
  aws iam simulate-principal-policy --policy-source-arn <role-arn> \
    --action-names s3:GetObject,iam:CreateUser,iam:AttachRolePolicy,sts:AssumeRole \
    --resource-arns '*' --output json --query 'EvaluationResults[].{Action:EvalActionName,Decision:EvalDecision}'
  ```
  This reveals whether the stolen credentials can create users, assume
  cross-account roles, or read S3 objects — critical for determining
  whether the attacker lateral-moved beyond the source account. Also
  check for cross-account trust policies:
  `aws iam get-role --role-name <name> --query 'Role.AssumeRolePolicyDocument'`
  — a role trusted by another account's principal means the stolen
  credentials work cross-account. Revoking credentials may break
  production workloads — have a replacement role ready.

- **Correlate with VPC Flow Logs for exfiltration confirmation.** For
  `Exfiltration:EC2/*` findings, confirm actual data movement by
  querying VPC Flow Logs for large outbound transfers to the
  exfiltration destination:
  ```bash
  aws logs start-query --log-group-name <vpc-flow-log-group> \
    --start-time <finding-eventFirstSeen-epoch> \
    --end-time <finding-eventLastSeen-epoch> \
    --query-string 'fields @timestamp, srcAddr, dstAddr, bytes, dstPort
      | filter srcAddr = "<instance-private-ip>" and isIpv4(dstAddr)
      | stats sum(bytes) as totalOut by dstAddr, dstPort
      | sort totalOut desc | limit 20'
  ```
  Look for: single-destination transfers exceeding 100 MB (sustained
  bulk exfiltration), connections to non-standard high ports (data
  exfiltration often uses 4444, 8443, 9999), and connections to known
  file-sharing endpoints (mega.co.nz, gofile.io, transfer.sh). If total
  outbound bytes to the flagged destination are under 1 MB, the
  exfiltration may be a probe, not a confirmed breach — adjust the
  REASON accordingly.

- **Prefer isolation over termination.** Isolation (security-group
  quarantine) is reversible; termination is not. A quarantined instance
  can be forensically examined; a terminated instance cannot. The ONLY
  case where immediate termination is justified is when the instance is
  actively causing harm (e.g., participating in a large DDoS attack) and
  isolation cannot stop the outbound traffic fast enough.

- **For suppression-filter creation (recurring FP):** verify the filter
  scope. `aws guardduty create-filter` with a too-broad criterion
  (e.g., filtering all `Recon:EC2/*` findings) hides genuine threats.
  Scope to the specific source IP, finding type, and resource ARN.

## Remediation guidance

### For CRITICAL findings (immediate IR)

1. **Isolate the affected resource.** For EC2: create and attach a
   quarantine security group with no inbound rules:
   ```bash
   QSG=$(aws ec2 create-security-group --group-name gd-quarantine-$(date +%s) \
     --description "GuardDuty quarantine — no inbound" --vpc-id <vpc-id> \
     --query GroupId --output text)
   aws ec2 modify-instance-attribute --instance-id <id> --groups $QSG
   ```
   For IAM: attach an inline Deny-all policy to the role/user (do not
   delete — preserve for investigation):
   ```bash
   aws iam put-role-policy --role-name <name> --policy-name DenyAll \
     --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":"*","Resource":"*"}]}'
   ```
2. **Revoke compromised credentials.** For instance-credential
   exfiltration: delete the stolen access keys and rotate the instance
   profile:
   ```bash
   aws iam delete-access-key --access-key-id <AKIA...> --user-name <role-session>
   aws iam list-access-keys --user-name <name>  # verify remaining keys
   ```
   For IAM-user compromise: deactivate all access keys and reset the
   password via the IAM console or `aws iam update-login-profile`.
3. **Capture forensic state.** EBS snapshot before any further changes:
   ```bash
   aws ec2 create-snapshot --volume-id <vol-id> \
     --description "GD-forensic-<finding-id>" \
     --tag-specifications 'ResourceType=snapshot,Tags=[{Key=Incident,Value=<id>}]'
   ```
   If SSM Agent is running on the instance, capture a memory forensic
   artifact via SSM Run Command before isolation (use the
   `AWS-ConfigureAWSPackage` document to install forensic tooling).
4. **Trace lateral movement.** Query CloudTrail for all API calls made
   by the compromised principal in the 24h before and after the finding:
   ```bash
   aws cloudtrail lookup-events --lookup-attributes \
     AttributeKey=Username,AttributeValue=<principal> \
     --start-time $(date -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date +%Y-%m-%dT%H:%M:%S)
   ```
   Look for `AssumeRole`, `GetObject`, `GetSecretValue`, and any
   infrastructure-modification calls.
5. **Notify the IR team.** CRITICAL findings should trigger the
   incident-response runbook. If the account has Security Hub enabled,
   the finding is already forwarded — verify the integration and check
   that the EventBridge rule for CRITICAL finding types routes to the
   IR pipeline (see "Security Hub integration" above).

### For HIGH findings (investigate within 4 hours)

1. **Verify the threat.** Check CloudTrail for the API call that triggered
   the finding. Confirm the source IP, the API action, and whether the
   action succeeded.
2. **Check for session validity.** For IAM findings, check whether the
   caller's session is still active (CloudTrail `userIdentity.sessionContext`).
3. **Rotate credentials if compromise is suspected.** For
   `MaliciousIPCaller` findings, rotate the access keys even if you
   cannot confirm compromise — the cost of rotation is low; the cost of
   a compromised key is high.
4. **Review security-group exposure.** For brute-force findings, check
   whether the security group restricts the targeted port to known CIDRs.
   If SSH/RDP is open to 0.0.0.0/0, tighten immediately.

### For MEDIUM findings (investigate within 24 hours)

1. **Contextualize the behavior.** Check whether the user/resource owner
   recognizes the activity (travel for console-login findings, scheduled
   job for API anomalies).
2. **Review the finding's `service.additionalInfo`.** This field often
   contains API call details, network-connection metadata, or DNS
   query specifics that help distinguish benign from malicious.
3. **Check for correlated findings.** A MEDIUM finding may be part of a
   kill-chain: Recon → Initial Access → Privilege Escalation. If a
   MEDIUM Recon finding precedes a HIGH UnauthorizedAccess finding on the
   same resource, escalate the pair.

### For LOW findings (monitor)

1. **Add to the monitoring queue.** No immediate action needed.
2. **Review exposed ports.** For PortProbeUnprotectedPort findings,
   verify the probed port should be open in the security group.
3. **Watch for escalation.** If the same source IP appears in a HIGH
   finding later, the LOW findings were reconnaissance for the attack.

### For LIKELY_FALSE_POSITIVE findings (archive)

1. **Archive the finding.** `aws guardduty archive-findings --detector-id
   <id> --finding-ids <fid>`.
2. **Create a suppression filter for recurring FPs.** If the same FP
   pattern recurs (same scanner IP, same DNS domain), create a filter:
   `aws guardduty create-filter --name suppress-nessus-scan
   --action '{"name": "ARCHIVE"}' --finding-criteria <json>`.
3. **Document the FP rationale.** Record WHY the finding was classified
   as FP (which pattern matched, what evidence supported it). This helps
   future analysts understand the suppression and prevents re-opening
   the finding.
4. **Periodically review suppression filters.** FP patterns change —
   a scanner IP that was authorized may become compromised. Review
   suppression filters quarterly.

## Recent AWS features (2024-2026)

- **Runtime Monitoring for ECS/EKS (2024-2025):** GuardDuty Runtime Monitoring provides runtime threat detection for ECS (Fargate and EC2) and EKS workloads, including new finding types like `RuntimeBehavior:ECS/AnomalousBehavior`, `RuntimeBehavior:EKS/AnomalousBehavior`, and `Trojan:ECS/*` / `Trojan:EKS/*`. Auditors should add these finding types to the Step 2/3 CRITICAL/HIGH lists — runtime malware detection on containers is a strong compromise signal.
- **Malware Protection v2 (2024-2025):** Enhanced malware scanning for EBS volumes with faster scan times and broader file-system coverage. New finding types include `Trojan:EC2/SuspiciousFile` with improved hash-based detection. The skill already covers `SuspiciousFile` as HIGH.
- **New detector types (2024-2025):** GuardDuty added new finding types including `Exfiltration:S3/AnomalousBehavior`, `Impact:S3/AnomalousBehavior`, and `DefenseEvasion:S3/*`. Auditors should verify that these finding types are not globally suppressed in archive filters — they represent high-value detections.
- **Network-origin behavior analytics (2024):** Enhanced network behavior analytics that detect anomalous outbound connections patterns. No new finding-type strings, but the existing `UnauthorizedAccess:EC2/MaliciousIPCaller` detections now include broader threat-intel correlation.
- **EKS Protection and RDS Protection (2024-2025):** GuardDuty now offers EKS Protection (runtime + API audit monitoring) and RDS Protection (brute-force detection for RDS). Auditors should verify these features are enabled on the detector.

## References

- AWS GuardDuty finding types:
  https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types.html
- GuardDuty severity levels:
  https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings.html#guardduty_findings-severity
- Managing GuardDuty findings (archive, suppress):
  https://docs.aws.amazon.com/guardduty/latest/ug/findings-manage.html
- GuardDuty trusted IP lists:
  https://docs.aws.amazon.com/guardduty/latest/ug/utils-trusted-ip.html
- MITRE ATT&CK Enterprise matrix:
  https://attack.mitre.org/matrices/enterprise/

## Security Hub integration and ASFF severity mapping

When GuardDuty forwards findings to AWS Security Hub, the numeric
severity (1.0-10.0) is mapped to the AWS Security Finding Format (ASFF)
`Severity.Label` field:

- 8.0 - 10.0 → `HIGH`
- 5.0 - 7.99 → `MEDIUM`
- 1.0 - 4.99 → `LOW`

Security Hub does NOT carry a CRITICAL label for GuardDuty findings —
the ASFF spec reserves CRITICAL for manual/imported findings. This means
the triage verdict CRITICAL (Step 2 active-compromise escalation) does
NOT round-trip through Security Hub. A finding classified as CRITICAL by
this skill will appear as HIGH in Security Hub.

**Operational implication:** when building Security Hub auto-response
rules (EventBridge rules that trigger on Security Hub findings), do NOT
filter solely on `Severity.Label == HIGH` for critical response — you
will miss findings that this skill escalates to CRITICAL. Instead, filter
on `Types` (finding-type strings) for the Step 2 CRITICAL list
(`Impact:EC2/CryptocurrencyClient`,
`UnauthorizedAccess:EC2/InstanceCredentialExfiltration.OutsideAWS`, etc.)
and route those to the IR pipeline regardless of the ASFF severity label.

**GuardDuty → Security Hub finding ID format:**
`arn:aws:securityhub:<region>:<account>:finding/<detector-id>/<finding-id>`.
When correlating a GuardDuty finding with its Security Hub counterpart,
strip the ARN prefix to get the raw finding ID for archival via
`aws guardduty archive-findings`.

## Section taxonomy (CloudOps auditor pattern)

This skill follows the CloudOps auditor skill pattern with a progressive
disclosure entry point:

1. **Frontmatter** — name, description, version, metadata.
2. **Triage in 30 seconds** — compact decision tree, severity map, and
   critical safety rules surfaced before deep content (progressive
   disclosure).
3. **Mindset** — the expert reasoning frame.
4. **Classification logic** — the ordered decision tree (Steps 0-7).
5. **Severity / risk matrix** — finding-type to verdict mapping table.
6. **Finding-type anatomy** — reference: type format, aggregation
   semantics, detection source confidence, additionalInfo deep fields,
   ECS/EKS edge cases.
7. **False-positive detection** — FP patterns with context signals.
8. **Output format** — the fixed per-finding report shape.
9. **NEVER** — anti-patterns with explicit reasoning.
10. **Pre-flight safety checks** — non-destructive operation guards.
11. **Remediation guidance** — per-verdict action plan.
12. **Security Hub integration** — ASFF severity mapping and EventBridge
    routing.

## Domain

AWS CloudOps / Security Operations & Threat Detection.

## AWS documentation

- **Amazon GuardDuty User Guide** — https://docs.aws.amazon.com/guardduty/latest/ug/what-is-guardduty.html
- **GuardDuty Security** — https://docs.aws.amazon.com/guardduty/latest/ug/security.html
- **GuardDuty API Reference** — https://docs.aws.amazon.com/guardduty/latest/APIReference/
- **GuardDuty CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/guardduty/
- **Runtime Monitoring for ECS/EKS** — https://docs.aws.amazon.com/guardduty/latest/ug/runtime-monitoring.html
- **GuardDuty finding types** — https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-active.html
