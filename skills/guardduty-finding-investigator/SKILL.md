---
name: guardduty-finding-investigator
description: >-
  Investigates Amazon GuardDuty findings through a finding-type-driven
  diagnostic tree covering Recon:IAMUser, UnauthorizedAccess:EC2,
  Backdoor:EC2, CryptoCurrency, Persistence:IAMUser, Policy:IAMUser,
  and Exfiltration families. Walks each finding to root cause by
  collecting evidence from CloudTrail (API actor, source IP,
  user-agent), VPC Flow Logs (egress patterns, foreign IPs), and
  CloudWatch (runtime metrics). Identifies false positives (authorized
  scanners, SaaS CIDR ranges, deployment pipelines), applies
  suppression rules via create-filter, and recommends auto-remediation
  via EventBridge to Lambda (isolate EC2, revoke IAM credentials,
  snapshot volumes for Malware Protection). Covers severity triage
  Low/Medium/High, Runtime Monitoring for ECS/EKS, EKS Protection, and
  Malware Protection chains. Emits ROOT_CAUSE_FOUND with the specific
  threat layer, NEED_MORE_INFO, or ESCALATE. Use when triaging a
  GuardDuty finding for security diagnosis, false-positive filtering,
  or containment decisions.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). Offline investigation works from pasted finding JSON
  or ASFF. Live-account investigation uses aws guardduty list-findings,
  get-findings, get-findings-statistics, aws cloudtrail lookup-events,
  aws ec2 describe-flow-logs, aws logs filter-log-events/get-query-results,
  aws ec2 describe-instances, aws iam get-access-key-last-used, aws s3api
  get-bucket-acl, and aws malware-scan (AWS CLI v2, SSO or key-based).
keywords:
  - GuardDuty
  - finding
  - threat detection
  - Recon:IAMUser
  - UnauthorizedAccess:EC2
  - Backdoor:EC2
  - CryptoCurrency
  - Persistence:IAMUser
  - Policy:IAMUser
  - Exfiltration
  - Runtime Monitoring
  - EKS Protection
  - Malware Protection
  - CloudTrail
  - VPC Flow Logs
  - false positive
  - suppression
  - auto-remediation
  - EventBridge
  - incident response
tags: [guardduty, security, threat-detection, incident-response, cloudtrail, vpc-flow-logs, troubleshooting, malware-protection, runtime-monitoring]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  when_to_use: >-
    Investigating a GuardDuty finding (single finding JSON, finding ID, or
    a list of findings from list-findings) for root cause, walking the
    finding-type family to the specific threat layer (credential abuse,
    crypto mining, SSH brute force, IAM persistence, S3 exfiltration,
    runtime process anomaly), collecting corroborating CloudTrail, VPC
    Flow Log, and CloudWatch evidence, identifying false positives
    (authorized scanners, known-safe SaaS CIDRs, deployment pipelines),
    applying suppression via create-filter, or recommending
    auto-remediation (isolate EC2, revoke IAM credentials, trigger
    Malware Protection scan). Diagnoses runtime threats — not config
    posture.
  when_not_to_use: >-
    Posture audits of GuardDuty configuration (use
    guardduty-finding-severity-triage for numeric severity
    classification, or the auditor family for detector enablement,
    trusted IP list, and org-level coverage). Non-GuardDuty detections
    (Inspector, Macie, Detective) use their own skills. Forensic chain
    of custody and disk imaging belong to incident-response-automator.
  activation_triggers:
    - "GuardDuty finding"
    - "GuardDuty alert"
    - "investigate GuardDuty"
    - "Recon:IAMUser"
    - "UnauthorizedAccess:EC2"
    - "Backdoor:EC2"
    - "CryptoCurrency"
    - "Persistence:IAMUser"
    - "Policy:IAMUser"
    - "Exfiltration"
    - "GuardDuty Runtime Monitoring"
    - "EKS Protection finding"
    - "Malware Protection scan"
    - "GuardDuty false positive"
    - "GuardDuty suppression filter"
    - "isolate EC2 from GuardDuty"
  invocation_schema: >-
    Input: either (a) a GuardDuty finding JSON (or finding ID + detector
    ID for live lookup), optionally paired with correlated CloudTrail,
    VPC Flow Log, or CloudWatch evidence; OR (b) a finding-type family
    and resource ARN for live-account investigation. Output: a
    deterministic FINDING/VERDICT/REASON/LAYER/EVIDENCE/SUPPRESSION/
    REMEDIATION block where VERDICT in {ROOT_CAUSE_FOUND, NEED_MORE_INFO,
    ESCALATE} and LAYER in {CREDENTIAL_ABUSE, CRYPTO_MINING,
    SSH_BRUTE_FORCE, IAM_PERSISTENCE, POLICY_CHANGE, DATA_EXFILTRATION,
    RUNTIME_ANOMALY, FALSE_POSITIVE, SUPPRESSED, AWS_SIDE, UNKNOWN}.
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

```bash
# Detector IDs and the finding itself (preferred path)
aws guardduty list-detectors --output json
aws guardduty get-findings --detector-id <detector-id> \
  --finding-ids <finding-id> --output json

# Finding statistics, trusted IPs, and enabled features
aws guardduty get-findings-statistics --detector-id <detector-id> \
  --finding-statistics-types COUNT_BY_SEVERITY COUNT_BY_TYPE --output json
aws guardduty list-ip-sets --detector-id <detector-id> --output json
aws guardduty list-threat-intel-sets --detector-id <detector-id> --output json
aws guardduty list-features --detector-id <detector-id> --output json

# CloudTrail lookup for the finding's actor and time window
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin \
  --start-time <finding-utc-minus-15m> --end-time <finding-utc-plus-15m>

# VPC Flow Log location (log group or S3) for the resource's VPC
aws ec2 describe-flow-logs --filter Name=resource-id,Values=<vpc-id> --output json

# AWS Health (regional events for GuardDuty)
aws health describe-events \
  --filter services=GUARDDUTY,eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

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

- **A finding from a "trusted" source IP is still a finding until the
  IP is in the trusted IP list.** GuardDuty does not deduce trust from
  on-prem CIDRs, SaaS ranges, or scanner hostnames. Prefer the Trusted
  IP list over suppression — the trusted IP list lets GuardDuty keep
  tracking the source's behaviour.

- **ConsoleLogin from a new AWS Region fires on the first successful
  login from that Region.** Travelling users trigger this once per
  Region. Either add their CIDRs to the trusted IP list, or accept the
  Low severity noise — never blanket-suppress.

- **CryptoCurrency:EC2/BitcoinTool.B!DNS fires on DNS, not on the
  binary.** A misconfigured app calling a domain that resolves to a
  pool will trigger. Corroborate with CloudWatch CPUUtilization before
  isolating.

- **Policy:IAMUser/S3BucketAnonymousGranted fires even for intentional
  public buckets** (website bucket, CloudFront origin). Confirm the
  change author and ticket, then suppress if intentional.

- **Runtime:EC2/ProcessA findings require the GuardDuty Security
  Agent installed.** If the agent is disabled or unsupported, Runtime
  findings will not fire — absence does not mean absence of runtime
  threats. EKS findings may originate from the host node (privileged
  DaemonSet), not the workload pod — inspect
  `resource.eksClusterDetails` and `resource.containerDetails`.

- **VPC Flow Logs capture only L3/L4 traffic.** DNS-over-HTTPS,
  encrypted C2, and tunneled egress look like benign TLS on port 443.
  For Backdoor/CryptoCurrency, supplement with Route 53 Resolver logs
  (DNS) and Malware Protection scans. Suppression filters using
  `equals` on the resource ARN break when the resource is recreated —
  use `equals` on the static attribute (instance profile, IAM user
  name, bucket name).

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

```bash
# Identify the probing source from the finding
jq '.service.action.portProbeAction.remoteIpDetails' finding.json
# ipAddressV4, organization {asn, org}, location {country, city}

# Compare against the trusted IP list
aws guardduty list-ip-sets --detector-id <detector-id> --output json
aws guardduty get-ip-set --detector-id <detector-id> \
  --ip-set-id <ip-set-id> --output json

# Check CloudTrail for the actor behind the probe (IAM findings only)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ListBuckets \
  --start-time <finding-utc-minus-30m> --end-time <finding-utc-plus-30m>
```

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

```bash
# CloudTrail burst pattern — List* / Get* calls
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=<iam-user> \
  --start-time <finding-utc-minus-15m> --end-time <finding-utc-plus-15m>
# Look for: ListBuckets, GetCallerIdentity, ListRoles, ListUsers bursts

# Access key last used (is the key still active?)
aws iam get-access-key-last-used --access-key-id <AKIA...>
```

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

```bash
# CloudTrail ConsoleLogin event
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin \
  --start-time <finding-utc-minus-15m> --end-time <finding-utc-plus-15m>
# Capture: sourceIPAddress, userIdentity.arn, additionalEventData.MFAUsed
aws iam get-login-profile --user-name <iam-user>
```

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

```bash
# VPC Flow Logs — concentration of dstport=22 from many source IPs
aws logs start-query --log-group-name <flow-log-group> \
  --start-time <epc-finding-utc-minus-30m> --end-time <epc-finding-utc-plus-30m> \
  --query-string 'fields @timestamp, srcAddr, dstAddr, dstPort
    | filter dstPort=22 and action=ACCEPT
    | stats count() by srcAddr | sort count desc | limit 20'

# Check the EC2 instance's security group — is port 22 open to 0.0.0.0/0?
aws ec2 describe-security-groups \
  --group-ids $(aws ec2 describe-instances --instance-ids <i-id> \
    --output json | jq -r '.Reservations[0].Instances[0].SecurityGroups[].GroupId') \
  --output json | jq '.SecurityGroups[].IpPermissions[] | select(.FromPort==22)'
```

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

```bash
# Extract the remote IP from the finding
jq '.service.action.networkConnectionAction.remoteIpDetails' finding.json

# VPC Flow Logs — sustained outbound to the suspicious IP
aws logs start-query --log-group-name <flow-log-group> \
  --start-time <epc-finding-utc-minus-1h> --end-time <epc-finding-utc-plus-1h> \
  --query-string 'fields @timestamp, srcAddr, dstAddr, dstPort, bytes
    | filter (srcAddr="<instance-private-ip>" and dstAddr="<remote-ip>")
    | sort @timestamp desc | limit 100'

# Route 53 Resolver logs (DNS-based C&C)
aws logs start-query --log-group-name <resolver-log-group> \
  --query-string 'fields @timestamp, srcaddr, query_name
    | filter srcaddr="<instance-private-ip>" | sort @timestamp desc'
```

**Verdict signals:**
- Sustained outbound to a ThreatintelSet-matched IP on non-standard
  ports → **ROOT_CAUSE_FOUND**, `LAYER: RUNTIME_ANOMALY` (treat as
  compromised). Containment: isolate the EC2 SG, snapshot EBS for
  Malware Protection scan, do NOT terminate (forensic state).
- Single short-lived connection, no other indicators →
  **ROOT_CAUSE_FOUND**, `LAYER: FALSE_POSITIVE` (drive-by scan,
  misconfigured app). Monitor but do not isolate.

### Step 5: CryptoCurrency:EC2 — crypto mining

```bash
# DNS variant — mining pool domain lookup
jq '.service.action.dnsRequestAction.domain' finding.json

# VPC Flow Logs — outbound to mining pool CIDRs (ports 3333, 4444, 8888, 14444)
aws logs start-query --log-group-name <flow-log-group> \
  --query-string 'fields @timestamp, srcAddr, dstAddr, dstPort, bytes
    | filter srcAddr="<instance-private-ip>" and
      (dstPort=3333 or dstPort=4444 or dstPort=8888 or dstPort=14444)
    | stats sum(bytes) by dstAddr'

# CloudWatch — CPU spike around the finding time
aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
  --metric-name CPUUtilization --dimensions Name=InstanceId,Value=<i-id> \
  --start-time <finding-utc-minus-1h> --end-time <finding-utc-plus-1h> \
  --period 300 --statistics Average,Maximum --output json
```

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

```bash
# CloudTrail — CreateUser, CreateAccessKey, AttachRolePolicy around the finding
for EV in CreateUser CreateAccessKey AttachUserPolicy; do
  aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=$EV \
    --start-time <finding-utc-minus-30m> --end-time <finding-utc-plus-30m>
done
```

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

```bash
# S3BucketAnonymousGranted — confirm the ACL change
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutBucketAcl \
  --start-time <finding-utc-minus-30m> --end-time <finding-utc-plus-30m>
aws s3api get-bucket-acl --bucket <bucket>

# RootCredentialUsage — root API call source
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=root \
  --start-time <finding-utc-minus-15m> --end-time <finding-utc-plus-15m>
```

**Verdict signals:**
- PutBucketAcl from a known deployment role, bucket is a documented
  public CloudFront origin (change ticket linked) →
  **ROOT_CAUSE_FOUND**, `LAYER: FALSE_POSITIVE`.
- Anonymous grant from an unexpected actor, or root credential used
  outside the documented break-glass procedure → **ROOT_CAUSE_FOUND**,
  `LAYER: POLICY_CHANGE` (treat as malicious). Revert the policy,
  investigate the actor's session context, rotate root credentials.

### Step 8: Exfiltration — data leaving the account

```bash
# S3 variant — anomalous GetObject volume (needs CloudTrail data events)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --start-time <finding-utc-minus-1h> --end-time <finding-utc-plus-1h>

# VPC Flow Logs — anomalous outbound volume
aws logs start-query --log-group-name <flow-log-group> \
  --query-string 'fields srcAddr, dstAddr, bytes
    | filter srcAddr="<instance-private-ip>"
    | stats sum(bytes) as totalBytes by dstAddr | sort totalBytes desc | limit 20'

# S3 access logs (for S3 exfil)
aws s3api get-bucket-logging --bucket <bucket>
```

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

```bash
# Inspect the runtime evidence from the finding itself
jq '.service.runtimeData' finding.json
# processDetails: name, path, pid, user, cmdline, parent
# networkConnection: direction, local, remote
# moduleInformation: loaded libraries

# CloudWatch Container Insights (ECS/EKS), EKS context, agent status
aws logs describe-log-groups --log-group-name-prefix /aws/ecs/containerinsights
jq '.resource.eksClusterDetails, .resource.containerDetails' finding.json
aws ssm describe-instance-information --filters Key=InstanceIds,Values=<i-id>
```

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

```bash
aws malware-scan start-malware-scan \
  --resource-arn arn:aws:ec2:<region>:<acct>:snapshot/<snap-id>
aws malware-scan list-scans --filter-criteria '<json>' --output json
aws malware-scan get-scan --scan-id <scan-id> --output json
```

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

- **Authorised scanner** — filter on
  `service.action.portProbeAction.remoteIpDetails.ipAddressV4` in
  `<scanner-cidr>` AND action = ARCHIVED.
- **AWS Config aggregator** — filter on
  `resource.accessKeyDetails.principalId` containing
  `AWSServiceRoleForConfig` AND `awsApiCallAction.api` = `ListBuckets`.
- **Deployment pipeline IAM burst** — filter on principalId containing
  `<deployment-role-name>` AND finding type in
  `Recon:IAMUser/UserPermissions`, `Persistence:IAMUser/UserCreation`.
- **Public S3 bucket (documented)** — filter on
  `resource.s3BucketDetails.name` = `<bucket>` AND finding type =
  `Policy:IAMUser/S3BucketAnonymousGranted`.

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

When triaging a finding, ask three questions in order. (1) Does the
finding's `service.action` field match the resource type? A
`networkConnectionAction` on an `AccessKey` is misattributed — treat
with suspicion. (2) Does the finding's actor (IAM user, source IP,
parent process) appear in another finding in the same time window?
Correlated findings across families (e.g., a ConsoleLogin success
followed by a Persistence:IAMUser finding) are a kill-chain signature;
either alone might be noise, together they are almost certainly a
compromise. (3) What does the operator's environment say? The trusted
IP list, the IAM role name, and the deployment pipeline pattern are the
three highest-signal contextual inputs. A finding matching all three is
almost certainly a false positive; matching none is almost certainly a
true positive; the middle case is where senior judgment matters most.

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

A Low-severity port-probe finding from `198.51.100.10` resolves to
FALSE_POSITIVE when the IP is the corporate Qualys scanner CIDR (verified
against `organization.org = "Qualys, Inc."` and the weekly scan window).
The block sets `LAYER: FALSE_POSITIVE`, recommends adding the CIDR to
the GuardDuty trusted IP list (`aws guardduty create-ip-set ... --activate`)
rather than suppressing the finding family, and confirms subsequent
weekly scans no longer produce `Recon:EC2/PortProbe` findings. The full
block format follows the STRICT output contract above; the key
suppression preference is **trusted IP list over archive filter** so
GuardDuty continues tracking the source.

## Domain

AWS CloudOps / Amazon GuardDuty Threat Investigation, CloudTrail
Forensics, VPC Flow Log Analysis, Runtime Threat Diagnosis, and
Incident Containment.

## Recent AWS features (2024-2026)

- **GuardDuty Runtime Monitoring (2024-2025):** GA for EC2, ECS
  (incl. Fargate), and EKS. The SSM-managed GuardDuty Security Agent
  reports process/network/module telemetry. Findings of the form
  `Runtime:EC2/ProcessA`, `Runtime:ECS/ProcessA`, `Runtime:EKS/ProcessA`
  require the agent installed and feature enabled per detector. Verify
  `aws guardduty list-features` shows Runtime Monitoring ENABLED.

- **GuardDuty EKS Protection (2024-2025):** Adds EKS audit-log
  monitoring alongside Runtime Monitoring. Findings attribute to the
  cluster via `resource.eksClusterDetails` and
  `resource.containerDetails` — distinguish audit-log findings (K8s API
  abuse) from Runtime findings (process behaviour). New K8s types
  include `UnauthorizedAccess:Kubernetes/SuccessfulAnonymousAccess`.

- **GuardDuty Malware Protection (2024-2025):** Scans EBS snapshots
  and S3 objects on-demand or via EventBridge. `aws malware-scan
  start-malware-scan` is the primary CLI. Scans are point-in-time — a
  clean scan does not prove the resource is malware-free in perpetuity.
  Malware Protection for S3 (GA 2024) auto-scans new objects on
  enabled buckets.

- **GuardDuty cross-account suppression (2024):** In Organizations
  with delegated admin, suppression filters created by the admin
  account propagate to member accounts — use the admin account for
  global rules.

- **GuardDuty RDS Protection (2024-2025):** GA, monitors RDS login
  anomalies (`UnauthorizedAccess:RDS/BruteForce`). VPC Flow Logs and
  RDS PostgreSQL/MySQL logs are the corroborating surfaces.

- **GuardDuty General Bucket Monitoring for S3 (2024):** Extended
  detection beyond Public Bucket Access — includes data-pattern
  exfiltration on private buckets. Tune via the S3 feature on the
  detector.

## AWS documentation

- **GuardDuty User Guide** — https://docs.aws.amazon.com/guardduty/latest/ug/
- **GuardDuty finding types** — https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types.html
- **Runtime Monitoring / EKS Protection / Malware Protection** — https://docs.aws.amazon.com/guardduty/latest/ug/runtime-monitoring.html
- **GuardDuty suppression rules** — https://docs.aws.amazon.com/guardduty/latest/ug/findings_suppression-rule-types.html
- **AWS CLI GuardDuty reference** — https://docs.aws.amazon.com/cli/latest/reference/guardduty/
- **CloudTrail lookup-events** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events-cli.html
