---
name: guardduty-finding-investigator
description: Investigates Amazon GuardDuty findings through a finding-type-driven diagnostic tree covering Recon:IAMUser, UnauthorizedAccess:EC2, Backdoor:EC2, CryptoCurrency, Persistence:IAMUser, Policy:IAMUser, and Exfiltration families. Walks each finding to root cause by collecting evidence from CloudTrail (API actor, source IP, user-agent), VPC Flow Logs (egress patterns, foreign IPs), and CloudWatch (runtime metrics). Identifies false positives (authorized scanners, SaaS CIDR ranges, deployment pipelines), applies suppression rules via create-filter, and recommends auto-remediation via EventBridge to Lambda (isolate EC2, revoke IAM credentials, snapshot volumes for Malware Protection). Covers severity triage Low/Medium/High, Runtime Monitoring for ECS/EKS, EKS Protection, and Malware Protection chains. Emits ROOT_CAUSE_FOUND with the specific threat layer, NEED_MORE_INFO, or ESCALATE. Use when triaging a GuardDuty finding for security diagnosis, false-positive filtering, or containment decisions.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline investigation works from pasted finding JSON or ASFF. Live-account investigation uses aws guardduty list-findings, get-findings, get-findings-statistics, aws cloudtrail lookup-events, aws ec2 describe-flow-logs, aws logs filter-log-events/get-query-results, aws ec2 describe-instances, aws iam get-access-key-last-used, aws s3api get-bucket-acl, and aws malware-scan (AWS CLI v2, SSO or key-based).
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
  when_to_use: Investigating a GuardDuty finding (single finding JSON, finding ID, or a list of findings from list-findings) for root cause, walking the finding-type family to the specific threat layer (credential abuse, crypto mining, SSH brute force, IAM persistence, S3 exfiltration, runtime process anomaly), collecting corroborating CloudTrail, VPC Flow Log, and CloudWatch evidence, identifying false positives (authorized scanners, known-safe SaaS CIDRs, deployment pipelines), applying suppression via create-filter, or recommending auto-remediation (isolate EC2, revoke IAM credentials, trigger Malware Protection scan). Diagnoses runtime threats — not config posture.
  when_not_to_use: Posture audits of GuardDuty configuration (use guardduty-finding-severity-triage for numeric severity classification, or the auditor family for detector enablement, trusted IP list, and org-level coverage). Non-GuardDuty detections (Inspector, Macie, Detective) use their own skills. Forensic chain of custody and disk imaging belong to incident-response-automator.
  activation_triggers: GuardDuty finding, GuardDuty alert, investigate GuardDuty, Recon:IAMUser, UnauthorizedAccess:EC2, Backdoor:EC2, CryptoCurrency, Persistence:IAMUser, Policy:IAMUser, Exfiltration, GuardDuty Runtime Monitoring, EKS Protection finding, Malware Protection scan, GuardDuty false positive, GuardDuty suppression filter, isolate EC2 from GuardDuty
  invocation_schema: 'Input: either (a) a GuardDuty finding JSON (or finding ID + detector ID for live lookup), optionally paired with correlated CloudTrail, VPC Flow Log, or CloudWatch evidence; OR (b) a finding-type family and resource ARN for live-account investigation. Output: a deterministic FINDING/VERDICT/REASON/LAYER/EVIDENCE/SUPPRESSION/ REMEDIATION block where VERDICT in {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and LAYER in {CREDENTIAL_ABUSE, CRYPTO_MINING, SSH_BRUTE_FORCE, IAM_PERSISTENCE, POLICY_CHANGE, DATA_EXFILTRATION, RUNTIME_ANOMALY, FALSE_POSITIVE, SUPPRESSED, AWS_SIDE, UNKNOWN}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: GuardDuty, finding, threat detection, Recon:IAMUser, UnauthorizedAccess:EC2, Backdoor:EC2, CryptoCurrency, Persistence:IAMUser, Policy:IAMUser, Exfiltration, Runtime Monitoring, EKS Protection, Malware Protection, CloudTrail, VPC Flow Logs, false positive, suppression, auto-remediation, EventBridge, incident response
  tags: guardduty, security, threat-detection, incident-response, cloudtrail, vpc-flow-logs, troubleshooting, malware-protection, runtime-monitoring
---

# GuardDuty Finding Investigator

## What this skill does

Walks an Amazon GuardDuty finding from raw JSON to a confirmed root
cause with positive evidence. The diagnostic tree is
**finding-type-family driven** (Recon, UnauthorizedAccess, Backdoor,
CryptoCurrency, Persistence, Policy, Exfiltration, Runtime). Each branch
collects specific corroborating evidence from CloudTrail (actor, source
IP), VPC Flow Logs (egress to suspicious CIDRs), and CloudWatch (runtime
metrics). The skill distinguishes true positives from common
false-positive patterns (authorized scanners, SaaS CIDR ranges, broken
deployment jobs) and emits a verdict with either a containment action or
a suppression rule.

## Mindset

A GuardDuty finding is a **signal**, not a conclusion. The detector saw
an anomaly; the operator must prove whether the anomaly is a threat, a
misclassified benign activity, or a noisy detector that needs
suppression. Senior GuardDuty engineers verify every finding against at
least one independent evidence source (CloudTrail for IAM, VPC Flow Logs
for network, CloudWatch for runtime) before recommending containment.
A finding without corroborating evidence is a hypothesis, not a root
cause.

## STRICT output contract

Every investigation MUST emit exactly one diagnostic block per finding:

```text
FINDING: <finding-id or finding-type:resource>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the threat layer and the corroborating evidence>
LAYER: <CREDENTIAL_ABUSE | CRYPTO_MINING | SSH_BRUTE_FORCE | IAM_PERSISTENCE |
        POLICY_CHANGE | DATA_EXFILTRATION | RUNTIME_ANOMALY | FALSE_POSITIVE |
        SUPPRESSED | AWS_SIDE | UNKNOWN>
SEVERITY: <LOW | MEDIUM | HIGH>
EVIDENCE:
  - <GuardDuty finding summary — type, resource, actor, severity>
  - <corroborating probe — CloudTrail event / VPC Flow record / CloudWatch metric>
  - <false-positive ruled out — name the FP class tested and why it does not apply>
SUPPRESSION:
  - <if FALSE_POSITIVE: create-filter JSON for archive rule>
  - <otherwise: "Not applicable — true positive">
REMEDIATION:
  1. <containment action with CLI command>
  2. <verification command after containment>
CONFIRM: Before any state-changing CLI (isolate instance, revoke keys,
  create suppression filter, trigger malware scan), emit and await operator
  approval: "CONFIRM: About to <action> on <resource>. Proceed? (yes/no)"
```

A block without EVIDENCE containing at least one GuardDuty field AND one
corroborating probe is a contract violation. ROOT_CAUSE_FOUND on a true
positive requires threat evidence; on a FALSE_POSITIVE layer, it
requires benign-context evidence.

## Quick navigation

| If the finding type is... | Go to | First corroborating probe |
|---|---|---|
| `Recon:EC2/PortProbe` / `Recon:IAMUser/PortProbe` | Step 2a | `sourceIp` vs trusted IP list |
| `Recon:IAMUser/UserPermissions` | Step 2b | CloudTrail `List*` / `GetCallerIdentity` burst |
| `UnauthorizedAccess:IAMUser/ConsoleLogin` (new geo) | Step 3a | CloudTrail `ConsoleLogin`, `sourceIpAddress`, MFAUsed |
| `UnauthorizedAccess:EC2/SSHBruteForce` / `RDPBruteForce` | Step 3b | VPC Flow Logs `dstport=22|3389`, src IP concentration |
| `Backdoor:EC2/Spambot` / `Backdoor:EC2/C&CActivity.B` | Step 4 | VPC Flow Logs egress to known-bad CIDRs |
| `CryptoCurrency:EC2/BitcoinTool.B` / `BitcoinTool.B!DNS` | Step 5 | VPC Flow Logs + CloudWatch CPU + Route 53 Resolver |
| `Persistence:IAMUser/UserCreation` / `IAMUser anomaly` | Step 6 | CloudTrail `CreateUser`, `CreateAccessKey`, `AttachRolePolicy` |
| `Policy:IAMUser/S3BucketAnonymousGranted` / `RootCredentialUsage` | Step 7 | CloudTrail `PutBucketAcl`, `sourceUserId=Root` |
| `Exfiltration:S3/AnomalousBehavior.S3` / `EC2/PortSweep` | Step 8 | VPC Flow Logs egress + S3 access logs |
| `Runtime:EC2/ECS/EKS/ProcessA` | Step 9 | CloudWatch Container Insights + GuardDuty Runtime evidence |
| Malware Protection scan needed | Step 10 | `aws malware-scan start-malware-scan` |

For the finding-type catalogue, severity bands, and suppression
patterns, see `references/finding-types-and-suppression.md`.

## Pre-flight: gather finding metadata

Before running any finding-type-specific probe, gather the canonical
finding metadata. A misread finding type (e.g., confusing
`UnauthorizedAccess:IAMUser/ConsoleLogin` with
`UnauthorizedAccess:EC2/SSHBruteForce`) routes the investigation to the
wrong layer.

### Account-wide pre-flight commands

Account-wide pre-flight command listing moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Account-wide pre-flight commands

### Finding-shape short-circuit

| Field | Value | Effect on investigation |
|---|---|---|
| `service.action` | `NETWORK_CONNECTION` / `DNS_REQUEST` / `PORT_PROBE` | Network-layer finding. VPC Flow Logs + Route 53 Resolver logs are the corroborating surface. |
| `service.action` | `AWS_API_CALL` | IAM-layer finding. CloudTrail is the corroborating surface. |
| `service.action` | `RDS_LOGIN` / `KINESIS_STREAM` | Service-specific finding. Service-level logs are the corroborating surface. |
| `service.runtimeData` | present | Runtime Monitoring finding. CloudWatch Container Insights + GuardDuty Runtime evidence are the corroborating surface. |
| `service.additionalInfo.threatListName` | present | GuardDuty matched a ThreatintelSet — high signal, treat as true positive until disproven. |
| `severity` | `0.1-1.9` Low / `2.0-6.9` Medium / `7.0-8.9` High | Drives escalation SLA, not the verdict. A Low finding can still be ROOT_CAUSE_FOUND if evidence is positive. |
| `resource.resourceType` | `Instance` / `AccessKey` / `S3Bucket` / `EksCluster` / `Container` | Determines which resource-specific probe applies. |

### Missing-context NEED_MORE_INFO

If the input is missing the finding JSON, finding ID, detector ID, or
sufficient resource context, emit a NEED_MORE_INFO block listing the
specific missing fields (finding ID, detector ID, time window) and the
next probe to run once available.

## Process — finding-type-driven decision tree

Pick the entry point based on the finding-type family, then walk the
type-specific probes in order. Each branch ends with either a positive
root-cause confirmation (corroborating evidence that matches the
finding) or a pass that moves to the next plausible layer. **Never emit
ROOT_CAUSE_FOUND without corroborating evidence from an independent
source.**

### Step 0: Non-obvious behaviours that change the diagnosis

Step 0 non-obvious behaviours moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Step 0: Non-obvious behaviours that change the diagnosis

### Step 1: Symptom entry — pick the diagnostic branch

Map the finding-type family to a branch. If the type is ambiguous,
first fetch the finding JSON: `aws guardduty get-findings --detector-id
<detector-id> --finding-ids <finding-id>` and inspect `service.action`
— the highest-signal classifier names the observed behaviour
(`NETWORK_CONNECTION`, `AWS_API_CALL`, `DNS_REQUEST`, `PORT_PROBE`,
`RDS_LOGIN`).

| Finding family | Meaning | Branch |
|---|---|---|
| **Recon:IAMUser*** / **Recon:EC2*** | Reconnaissance — port probes, permission discovery | Step 2 |
| **UnauthorizedAccess:IAMUser/ConsoleLogin** / **UnauthorizedAccess:EC2/SSH/RDP*** | Unauthorized access — credential or brute force | Step 3 |
| **Backdoor:EC2*** | Instance communicating with known C&C or spambot infrastructure | Step 4 |
| **CryptoCurrency:EC2*** | Crypto-currency mining activity (DNS or binary) | Step 5 |
| **Persistence:IAMUser*** | Anomalous IAM changes that establish persistence | Step 6 |
| **Policy:IAMUser*** | Suspicious policy or ACL grants (anonymous S3, root credential) | Step 7 |
| **Exfiltration:S3*** / **Exfiltration:EC2*** | Data leaving the account in an anomalous pattern | Step 8 |
| **Runtime:EC2*** / **Runtime:ECS*** / **Runtime:EKS*** | Runtime Monitoring detected malicious process behaviour | Step 9 |
| `aws malware-scan` requested or Malware Protection scan pending | Scan trigger needed | Step 10 |

### Step 2: Recon:IAMUser / Recon:EC2 — reconnaissance

Symptom: a resource is probing AWS API permissions or scanning network
ports. Most Recon findings are Low severity and frequently false
positives.

#### 2a: Port probe findings (`Recon:EC2/PortProbe` or `Recon:IAMUser/PortProbe`)

Probe commands moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Step 2a: Recon — port probe commands

**Verdict signals:**
- Source IP matches a known scanner (authorised security scanner, AWS
  Config aggregator, SaaS posture manager CIDR) → **ROOT_CAUSE_FOUND**,
  `LAYER: FALSE_POSITIVE`. Add the scanner CIDR to the trusted IP list
  (preferred) or archive via `create-filter`.
- AWS Config aggregator calling ListBuckets → known GuardDuty noise.
  **ROOT_CAUSE_FOUND**, `LAYER: FALSE_POSITIVE`. Suppress on
  `awsApiCallAction.api = ListBuckets` AND principalId containing
  `AWSServiceRoleForConfig`.
- Source IP unknown, ASN ties to a hosting provider, multiple ports
  probed → corroborate with VPC Flow Logs and treat as **Step 4**
  (Backdoor / C&C candidate).

#### 2b: IAM permission discovery (`Recon:IAMUser/UserPermissions`)

Probe commands moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Step 2b: Recon — IAM permission discovery commands

**Verdict signals:**
- API calls match a known automation (Terraform plan, AWS Config,
  IAM Access Analyzer) on a CI host → **ROOT_CAUSE_FOUND**,
  `LAYER: FALSE_POSITIVE`.
- API calls originate from an unfamiliar region or user-agent with a
  burst of `List*` calls — suspicious enumeration.
  **ROOT_CAUSE_FOUND**, `LAYER: CREDENTIAL_ABUSE`. Move to IAM
  containment (Step 6).

### Step 3: UnauthorizedAccess — credential abuse or brute force

#### 3a: ConsoleLogin from a new geography or account (`UnauthorizedAccess:IAMUser/ConsoleLogin`)

Probe commands moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Step 3a: UnauthorizedAccess — ConsoleLogin commands

**Verdict signals:**
- `additionalEventData.MFAUsed == Yes`, source IP in the user's
  corporate egress CIDR, `userIdentity.sessionContext` shows a known
  SSO provider → **ROOT_CAUSE_FOUND**, `LAYER: FALSE_POSITIVE`. Add the
  corporate egress CIDR to the trusted IP list or suppress.
- MFA not used, source IP from an unexpected country, user has not
  logged in for > 30 days → **ROOT_CAUSE_FOUND**,
  `LAYER: CREDENTIAL_ABUSE`. Disable the user, revoke active sessions,
  rotate credentials (Step 6 containment).

#### 3b: SSH/RDP brute force (`UnauthorizedAccess:EC2/SSHBruteForce` or `RDPBruteForce`)

Probe commands moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Step 3b: UnauthorizedAccess — SSH/RDP brute force commands

**Verdict signals:**
- Many distinct source IPs attempting port 22 over a short window,
  instance SG allows 0.0.0.0/0 on port 22 → **ROOT_CAUSE_FOUND**,
  `LAYER: SSH_BRUTE_FORCE`. Containment: tighten the SG to corporate
  CIDR, install fail2ban or use EC2 Instance Connect, investigate
  whether any login succeeded (auth.log).
- Single source IP, low attempt count — likely a single misconfigured
  client, NOT a brute force. **ROOT_CAUSE_FOUND**, `LAYER: FALSE_POSITIVE`.

### Step 4: Backdoor:EC2 — C&C or spambot communication

Symptom: instance is communicating with known C&C infrastructure
(GuardDuty ThreatintelSet match) or exhibiting spambot behaviour.

Probe commands moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Step 4: Backdoor:EC2 — C&C / spambot commands

**Verdict signals:**
- Sustained outbound to a ThreatintelSet-matched IP on non-standard
  ports → **ROOT_CAUSE_FOUND**, `LAYER: RUNTIME_ANOMALY` (treat as
  compromised). Containment: isolate the EC2 SG, snapshot EBS for
  Malware Protection scan, do NOT terminate (forensic state).
- Single short-lived connection, no other indicators →
  **ROOT_CAUSE_FOUND**, `LAYER: FALSE_POSITIVE` (drive-by scan,
  misconfigured app). Monitor but do not isolate.

### Step 5: CryptoCurrency:EC2 — crypto mining

Probe commands moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Step 5: CryptoCurrency:EC2 — crypto mining commands

**Verdict signals:**
- DNS mining-pool domain AND sustained high CPU (> 80% across the
  finding window) AND outbound traffic on mining-pool ports →
  **ROOT_CAUSE_FOUND**, `LAYER: CRYPTO_MINING`. Containment: isolate
  the instance, snapshot for Malware Protection scan, investigate the
  compromise vector (over-permissive IAM role, vulnerable app, leaked
  SSH key).
- DNS hit only, CPU flat, no outbound mining-pool traffic — likely a
  domain that resolves to a mining-pool IP but is not used for mining
  (CDN edge, parked domain, drive-by DNS). **ROOT_CAUSE_FOUND**,
  `LAYER: FALSE_POSITIVE`. Suppress if the application legitimately
  uses the domain.

### Step 6: Persistence:IAMUser — anomalous IAM changes

Probe commands moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Step 6: Persistence:IAMUser — anomalous IAM change commands

**Verdict signals:**
- CreateUser / CreateAccessKey from an authorised CI/CD pipeline
  (`userIdentity.arn` contains the deployment role, source IP is the
  build host) and the new user matches a Terraform plan →
  **ROOT_CAUSE_FOUND**, `LAYER: FALSE_POSITIVE`. Suppress on the
  deployment role.
- CreateUser from an unexpected actor, new user has
  AdministratorAccess, and the access key was used from an unfamiliar
  IP within minutes → **ROOT_CAUSE_FOUND**, `LAYER: IAM_PERSISTENCE`.
  Containment: delete the rogue user, revoke the access key, rotate
  the actor's credential, scope blast radius with CloudTrail.

### Step 7: Policy:IAMUser — suspicious policy grants

Probe commands moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Step 7: Policy:IAMUser — suspicious policy grant commands

**Verdict signals:**
- PutBucketAcl from a known deployment role, bucket is a documented
  public CloudFront origin (change ticket linked) →
  **ROOT_CAUSE_FOUND**, `LAYER: FALSE_POSITIVE`.
- Anonymous grant from an unexpected actor, or root credential used
  outside the documented break-glass procedure → **ROOT_CAUSE_FOUND**,
  `LAYER: POLICY_CHANGE` (treat as malicious). Revert the policy,
  investigate the actor's session context, rotate root credentials.

### Step 8: Exfiltration — data leaving the account

Probe commands moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Step 8: Exfiltration — data-leaving-account commands

**Verdict signals:**
- Outbound bytes 10x baseline to an unfamiliar ASN, GetObject burst on
  a sensitive bucket → **ROOT_CAUSE_FOUND**,
  `LAYER: DATA_EXFILTRATION`. Containment: revoke the credential,
  isolate the instance, contact the data owner, engage legal if PII
  involved.
- Outbound spike matches a known daily batch job (corporate data
  warehouse load, scheduled backup to S3 in another account) →
  **ROOT_CAUSE_FOUND**, `LAYER: FALSE_POSITIVE`. Baseline the
  legitimate pattern; consider suppression.

### Step 9: Runtime Monitoring findings (`Runtime:EC2/ECS/EKS/ProcessA`)

Probe commands moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Step 9: Runtime Monitoring findings commands

**Verdict signals:**
- `processDetails.name` matches a known malicious binary (e.g.,
  `xmrig`, `kinsing`, `kdevtmpfsi`), parent process is a web server or
  container entrypoint → **ROOT_CAUSE_FOUND**, `LAYER: RUNTIME_ANOMALY`
  (treat as compromised). Containment: isolate the EC2 instance or
  terminate the compromised pod (`kubectl delete pod`), snapshot for
  Malware Protection scan, scope the entry vector.
- Process name matches a known false positive (CI runner named `agent`,
  APM sidecar named `collector`, Cron DaemonSet) and the parent process
  is the container entrypoint with a documented image →
  **ROOT_CAUSE_FOUND**, `LAYER: FALSE_POSITIVE`. Add the process path
  to the GuardDuty suppression filter scoped to the workload.

### Step 10: Malware Protection scan

Probe commands moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Step 10: Malware Protection scan commands

**Verdict signals:**
- Scan returns `INFECTED` with a named malware family →
  **ROOT_CAUSE_FOUND**, `LAYER: RUNTIME_ANOMALY` (confirmed malware).
  Continue containment and IR.
- Scan returns `CLEAN` → no malware on the snapshot. The runtime
  finding may still be valid (in-memory-only payload, fileless
  malware, scan timing). Do NOT downgrade to FALSE_POSITIVE on a clean
  scan alone — corroborate with VPC Flow Logs and process evidence.

### Step 11: Suppression rules — when and how

Apply suppression (archive filter) only after a finding is confirmed
FALSE_POSITIVE. The filter criterion should be **specific** (scoped to
the resource, actor, or API) — never blanket-suppress a finding family.

```bash
aws guardduty create-filter --detector-id <detector-id> \
  --name <filter-name> --action ARCHIVED \
  --finding-criteria '<json-criteria>' \
  --description "Suppress <FP reason>" --rank 1
```

**Suppression patterns by FP class** (full criteria JSON in
`references/finding-types-and-suppression.md`):

Suppression-pattern bullets moved to references.
→ [references/finding-types-and-suppression.md](references/finding-types-and-suppression.md) § Suppression patterns by FP class

### Step 12: Auto-remediation via EventBridge → Lambda

For High-severity true positives, recommend an EventBridge rule
(`source: aws.guardduty`, severity filter `[5,6,7,8]`) triggering a
Lambda for automated containment: EC2 → isolate SG (quarantine SG); IAM
→ deactivate access key + attach Deny-all policy; S3 → revert public
ACL; Runtime → trigger `aws malware-scan` on snapshot. Always post to
SOC chat — NEVER auto-terminate the resource.

### Step 13: Escalate or NEED_MORE_INFO

If no probe produced a positive root-cause match, OR the finding
indicates an AWS-side issue (region event, detector bug), emit:

- **ESCALATE** — AWS-side incident or threat beyond the operator's
  scope (APT indicators, regulated-data exfil, multi-account
  compromise). Surface the AWS Health event ARN, finding ID, and AWS
  Support case recommendation.
- **NEED_MORE_INFO** — A probe requires operator input (VPC Flow Logs
  not enabled, CloudTrail data events off, agent missing). List the
  missing pieces and the next probe to run once available.

## NEVER (top 5)

- **NEVER declare ROOT_CAUSE_FOUND without corroborating evidence from
  an independent source.** A GuardDuty finding is a hypothesis, not a
  root cause. CloudTrail for IAM, VPC Flow Logs for network, CloudWatch
  for runtime — at least one must independently confirm.

- **NEVER auto-terminate an EC2 instance as containment.** Termination
  destroys forensic state. The correct containment is SG isolation
  (quarantine SG with no in/out rules), then snapshot for Malware
  Protection scan and forensic analysis.

- **NEVER suppress a finding family with a blanket rule.** Suppressing
  all `CryptoCurrency:EC2*` or all `Recon:IAMUser*` hides real threats.
  Always scope suppression to a specific resource, actor, or source IP
  via create-filter; prefer the trusted IP list for known-benign
  sources.

- **NEVER assume a Low-severity finding is a false positive.** Severity
  is GuardDuty's confidence, not the operator's. A Low-severity
  ConsoleLogin from a new country may be the first indicator of a
  credential compromise. Verify with CloudTrail before suppressing.

- **NEVER downgrade a finding to FALSE_POSITIVE based on a clean
  Malware Protection scan alone.** Fileless malware, in-memory
  payloads, and scan-timing races can all produce clean results.
  Corroborate with VPC Flow Logs and process evidence first.

## Expert heuristic

Expert heuristic deep dive moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Expert heuristic

## Output format

See **STRICT output contract** above. Every investigation emits exactly
one diagnostic block per finding. A CONFIRMATION gate precedes any
state-changing CLI.

### Worked example — CryptoCurrency:EC2/BitcoinTool.B!DNS

```text
FINDING: a1b2c3d4 (CryptoCurrency:EC2/BitcoinTool.B!DNS on i-app-1)
VERDICT: ROOT_CAUSE_FOUND
REASON: i-app-1 queried a known mining-pool domain (miningpool.example)
  with sustained 95% CPUUtilization for the 90 minutes preceding the
  finding, plus outbound VPC Flow traffic on port 3333 to a Stratum pool
  endpoint (Step 5).
LAYER: CRYPTO_MINING
SEVERITY: HIGH
EVIDENCE:
  - GuardDuty finding: service.action.dnsRequestAction.domain =
    "miningpool.example", resource.instanceDetails.instanceId = i-app-1,
    severity = 7.5.
  - CloudWatch CPUUtilization on i-app-1: Average 95.2%, Maximum 99.8%
    across the 90-minute window preceding the finding.
  - VPC Flow Logs: sustained outbound from <instance-private-ip> to
    203.0.113.55 on dstPort=3333, 2.1 MB total egress in the window.
  - FP ruled out: app on i-app-1 is a Node.js API server with no DNS
    dependency on miningpool.example; the domain is not in the
    application's dependencies or code repository.
SUPPRESSION: Not applicable — true positive.
REMEDIATION:
  1. Isolate i-app-1 by attaching sg-quarantine (no in/out rules):
     aws ec2 modify-instance-attribute --instance-id i-app-1
       --groups sg-quarantine --profile <p>
  2. Snapshot the root EBS volume for Malware Protection scan:
     aws ec2 create-snapshots --instance-specification InstanceId=i-app-1
     aws malware-scan start-malware-scan --resource-arn <snapshot-arn>
  3. Investigate the compromise vector: IAM role on i-app-1, recent
     deployments, exposed credentials.
  4. Verify: describe-instances shows sg-quarantine; VPC Flow Logs show
     no further outbound traffic.
CONFIRM: "CONFIRM: About to modify-instance-attribute on i-app-1
  (isolate to sg-quarantine). This disconnects the app. Proceed? (yes/no)"
```

### Worked example — Recon:IAMUser/PortProbe (authorised scanner FP)

Full worked example moved to references.
→ [references/worked-examples.md](references/worked-examples.md) § Worked example — Recon:IAMUser/PortProbe (authorised scanner FP)

## References (load on demand)

Consult these only when the corresponding topic comes up:

- [references/finding-types-and-suppression.md](references/finding-types-and-suppression.md) — finding-type catalogue, severity bands, suppression criteria, and the FP-class suppression patterns (moved from Step 11)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — account-wide pre-flight commands and every per-step probe command listing (moved from Pre-flight and Steps 2-10)
- [references/worked-examples.md](references/worked-examples.md) — the authorised-scanner false-positive worked example (moved from § Output format)
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 non-obvious behaviours, the three-question expert heuristic, and recent AWS features (moved verbatim)
## Domain

AWS CloudOps / Amazon GuardDuty Threat Investigation, CloudTrail
Forensics, VPC Flow Log Analysis, Runtime Threat Diagnosis, and
Incident Containment.

## Recent AWS features (2024-2026)

2024-2026 GuardDuty feature notes moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Recent AWS features (2024-2026)

## AWS documentation

- **GuardDuty User Guide** — https://docs.aws.amazon.com/guardduty/latest/ug/
- **GuardDuty finding types** — https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types.html
- **Runtime Monitoring / EKS Protection / Malware Protection** — https://docs.aws.amazon.com/guardduty/latest/ug/runtime-monitoring.html
- **GuardDuty suppression rules** — https://docs.aws.amazon.com/guardduty/latest/ug/findings_suppression-rule-types.html
- **AWS CLI GuardDuty reference** — https://docs.aws.amazon.com/cli/latest/reference/guardduty/
- **CloudTrail lookup-events** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events-cli.html
