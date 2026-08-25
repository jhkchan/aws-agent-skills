# Advanced Patterns — GuardDuty Finding Severity Triage

Expert-knowledge deep dives, band rationales, overlay edge cases, and recent-feature notes, moved verbatim from SKILL.md. Load on demand.

## Mindset — full triage framing (moved from SKILL.md)

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

## Step 2 intro — why active-compromise types are CRITICAL

If the finding type is in the active-compromise list below, output
**CRITICAL** regardless of the numeric severity. These finding types
indicate a confirmed or near-confirmed active threat — the resource is
compromised and is being used for malicious purposes. GuardDuty may
assign these severity 8.0 (HIGH band), but the triage severity is CRITICAL
because the finding represents an ongoing incident, not a risk to
investigate.

## Severity escalation to CRITICAL (from HIGH numeric)

**Severity escalation to CRITICAL (from HIGH numeric):**
Even if GuardDuty assigns these a severity below 8.0, the triage verdict is
CRITICAL. The numeric severity reflects the threat family, not the
operational urgency. Crypto mining, credential exfiltration, and confirmed
C2 are all immediate-IR scenarios where the response time directly
determines blast radius.

## Step 7 overlay edge cases — escalation cap, missing count, FP-source exemption

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

## Resource-criticality detection signals (Step 7 detail)

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

## Confidence-signal de-escalation (Step 7 detail)

**Confidence-signal de-escalation:** If the finding's confidence is LOW
(GuardDuty reports a `confidence` value below 0.5, or the finding type
is ML-based with known high false-positive rates), AND no other context
confirms the threat, consider noting reduced confidence in the REASON
field. Do not auto-de-escalate based on confidence alone — low confidence
on a CRITICAL finding type (crypto mining) still warrants CRITICAL
response because the cost of missing a real threat exceeds the cost of
a false alarm.

## Severity / risk matrix (moved from SKILL.md)

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

## GuardDuty finding-type anatomy (reference detail: anatomy, aggregation, detection confidence, additionalInfo, ECS/EKS edge cases)

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

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Runtime Monitoring for ECS/EKS (2024-2025):** GuardDuty Runtime Monitoring provides runtime threat detection for ECS (Fargate and EC2) and EKS workloads, including new finding types like `RuntimeBehavior:ECS/AnomalousBehavior`, `RuntimeBehavior:EKS/AnomalousBehavior`, and `Trojan:ECS/*` / `Trojan:EKS/*`. Auditors should add these finding types to the Step 2/3 CRITICAL/HIGH lists — runtime malware detection on containers is a strong compromise signal.
- **Malware Protection v2 (2024-2025):** Enhanced malware scanning for EBS volumes with faster scan times and broader file-system coverage. New finding types include `Trojan:EC2/SuspiciousFile` with improved hash-based detection. The skill already covers `SuspiciousFile` as HIGH.
- **New detector types (2024-2025):** GuardDuty added new finding types including `Exfiltration:S3/AnomalousBehavior`, `Impact:S3/AnomalousBehavior`, and `DefenseEvasion:S3/*`. Auditors should verify that these finding types are not globally suppressed in archive filters — they represent high-value detections.
- **Network-origin behavior analytics (2024):** Enhanced network behavior analytics that detect anomalous outbound connections patterns. No new finding-type strings, but the existing `UnauthorizedAccess:EC2/MaliciousIPCaller` detections now include broader threat-intel correlation.
- **EKS Protection and RDS Protection (2024-2025):** GuardDuty now offers EKS Protection (runtime + API audit monitoring) and RDS Protection (brute-force detection for RDS). Auditors should verify these features are enabled on the detector.

## Additional AWS reference links (legacy References section, moved from SKILL.md)

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

## Security Hub integration and ASFF severity mapping (moved from SKILL.md)

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

## Section taxonomy (CloudOps auditor pattern) (moved from SKILL.md)

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

