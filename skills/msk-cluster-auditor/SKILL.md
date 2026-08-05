---
name: msk-cluster-auditor
description: >-
  Audits Amazon MSK (Managed Streaming for Kafka) clusters for encryption
  in-transit (TLS between clients and brokers, inter-broker), encryption
  at-rest (customer-managed KMS key), client authentication (TLS/IAM/SCRAM/
  unauthenticated), broker logging (CloudWatch/S3/Firehose), and public
  access exposure (private vs public subnets, SERVICE_PROVIDED_EIPS). Emits
  a deterministic categorical verdict per cluster. Use when reviewing MSK
  cluster security, checking Kafka encryption settings, validating client
  authentication modes, auditing broker logging coverage, or assessing
  public access exposure before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config classification. Live-account
  audits use aws kafka describe-cluster, aws kafka describe-configuration, and
  aws kafka list-clusters (AWS CLI v2, SSO or key-based credentials).
keywords:
  - MSK
  - Managed Kafka
  - Kafka
  - cluster audit
  - encryption in-transit
  - TLS
  - encryption at-rest
  - KMS
  - client authentication
  - SASL
  - SCRAM
  - IAM auth
  - mTLS
  - unauthenticated
  - broker logging
  - CloudWatch
  - public access
  - plaintext
  - broker security
  - MSK Serverless
  - cluster hardening
  - TLS_PLAINTEXT
tags: [msk, kafka, security, cluster-audit, encryption, authentication, logging, public-access, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  verdict_shape: "NO_ENCRYPTION | UNAUTHENTICATED | PUBLIC_ACCESS | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an MSK cluster before production deployment, checking Kafka
    encryption in-transit settings, validating client authentication modes,
    auditing broker logging coverage, assessing public access exposure, or
    hardening MSK cluster security posture.
  activation_triggers:
    - "audit this MSK cluster"
    - "is my Kafka cluster encrypted"
    - "check MSK authentication"
    - "MSK unauthenticated access"
    - "is my MSK cluster public"
    - "check MSK broker logging"
    - "harden MSK cluster"
    - "Kafka plaintext broker"
  invocation_schema: >-
    Input: either (a) an MSK cluster configuration (describe-cluster output or
    equivalent JSON), optionally paired with MSK configuration (Kafka broker
    settings), OR (b) a cluster ARN/name for live-account audit.
    Output: deterministic CLUSTER/VERDICT/REASON/FINDINGS/REMEDIATION block
    per cluster, where VERDICT is one of NO_ENCRYPTION, UNAUTHENTICATED,
    PUBLIC_ACCESS, CONFIG_GAP, OK.
---

# MSK Cluster Auditor

## Mindset

**One-line takeaway:** the verdict is always the **first matching condition**
in priority order — NO_ENCRYPTION beats UNAUTHENTICATED beats PUBLIC_ACCESS
beats CONFIG_GAP beats OK. Plaintext data on the wire dwarfs every other
finding because it exposes every Kafka message to network-level interception.

MSK runs managed Apache Kafka brokers inside an AWS VPC. Five dimensions
determine cluster security posture, and their severity is NOT equal:

- **Encryption in-transit** is the wire-level guarantee. With
  `ClientBroker: PLAINTEXT`, every Kafka message, credential, and payload
  travels unencrypted between clients and brokers. `TLS_PLAINTEXT` is
  equally dangerous — it allows clients to choose plaintext, defeating the
  encryption guarantee.
- **Client authentication** determines who can connect. `UNAUTHENTICATED:
  enabled` means anyone who can reach the brokers (VPC-peered, on-prem
  via Direct Connect, or internet-routed) can produce and consume without
  any identity check.
- **Public access** exposes brokers to the internet via Elastic IPs. Even
  with TLS and auth, an internet-reachable broker is an attack surface
  that should not exist in most deployments.
- **Broker logging** is the forensic record. With all log destinations
  disabled, you cannot answer "who produced what, and when" during an
  incident.
- **Encryption at-rest (KMS)** controls key governance. MSK always
  encrypts data volumes — the question is whether you control the key
  (customer-managed CMK with rotation + policy) or AWS does (AWS-managed
  key, no rotation control, shared across the account).

## Quick reference — verdict priority matrix

| # | Condition | Verdict | Priority |
|---|---|---|---|
| 1 | `ClientBroker: PLAINTEXT` OR `ClientBroker: TLS_PLAINTEXT` | **NO_ENCRYPTION** | Highest |
| 2 | `ClientAuthentication.Unauthenticated.enabled: true` | **UNAUTHENTICATED** | |
| 3 | `PublicAccess.Type: SERVICE_PROVIDED_EIPS` | **PUBLIC_ACCESS** | |
| 4 | All broker logging destinations disabled; OR no customer-managed KMS key (AWS-managed only) | **CONFIG_GAP** | |
| 5 | All dimensions pass | **OK** | Lowest |

The first matching row is the final verdict — subsequent dimensions produce
additional findings in the FINDINGS list but do not change the verdict.

## Pre-flight: cluster metadata gate (run before classification)

Several cluster attributes short-circuit the audit or change the
classification logic. Misclassifying them produces false positives.

| Attribute | Value | Effect on audit |
|---|---|---|
| `ClusterType` | `SERVERLESS` | **MSK Serverless.** Encryption in-transit is ALWAYS TLS (forced), at-rest is ALWAYS encrypted with a customer-managed key by default, auth is ALWAYS IAM, public access is NOT supported. Skip Steps 1-3 (always pass). Audit only logging (Step 4). |
| `ClusterType` | `PROVISIONED` | Proceed with full audit (Steps 1-5). |
| `State` | `CREATING` | Cluster not yet live — skip audit, output advisory. |
| `State` | `DELETING` / `FAILED` | Cluster is being torn down or failed — skip audit, output advisory. |
| `State` | `MAINTENANCE` | Cluster is undergoing AWS-side maintenance — audit normally but note brokers may be restarting. |
| `EncryptionInfo` | absent | Encryption settings unknown — this only happens on very old clusters or malformed input. Output `VERDICT: CONFIG_GAP` with "Encryption configuration not reported by describe-cluster — re-fetch with aws kafka describe-cluster." |

**If the cluster JSON is malformed** (invalid JSON, missing required fields
like `ClusterArn` or `ClusterName`), output:

```text
CLUSTER: <name or "unknown">
VERDICT: ERROR
REASON: Cluster configuration is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws kafka describe-cluster --cluster-arn <arn> --region <region>` and re-audit.
```

## Process — Classification logic (apply in order, first match is the verdict)

### Step 0: Expert knowledge — non-obvious MSK behaviors that change classification

Each behavior below changes a verdict if ignored:

- **`TLS_PLAINTEXT` is NOT "TLS with a plaintext fallback."** It is a
  dual-mode listener that publishes BOTH a TLS port and a plaintext port.
  Clients can choose either — the plaintext path carries every message
  unencrypted. Classify `TLS_PLAINTEXT` as **NO_ENCRYPTION**, not
  CONFIG_GAP. The encryption guarantee is broken the moment a plaintext
  path exists. A client connecting over plaintext bypasses TLS entirely;
  there is no downgrade negotiation, just two open doors.

- **`InClusterEncryption` is independent of `ClientBroker`.**
  `ClientBroker: TLS` encrypts client-to-broker traffic.
  `InClusterEncryption: true` encrypts broker-to-broker (inter-broker)
  traffic. A cluster with `ClientBroker: TLS` + `InClusterEncryption:
  false` encrypts the client wire but sends data in plaintext between
  brokers (often cross-AZ). Flag missing `InClusterEncryption` as a
  CONFIG_GAP finding — it does NOT rise to NO_ENCRYPTION because the
  client wire is still encrypted.

- **MSK always encrypts data volumes at rest.** There is no
  "unencrypted at rest" state — the `EncryptionAtRest` field, if present,
  names the KMS key; if absent, MSK uses an AWS-managed CMK
  (`alias/aws/kafka`). The audit question is governance, not presence:
  a customer-managed key gives you rotation control, key-policy audit,
  and CloudTrail decrypt visibility. An AWS-managed key rotates on AWS's
  schedule with no customer visibility. Missing a customer-managed key is
  CONFIG_GAP, not OK — but it is NOT NO_ENCRYPTION because data is still
  encrypted.

- **MSK Serverless has fundamentally different security defaults.**
  Serverless clusters enforce TLS in-transit, use IAM auth exclusively,
  do not support UNAUTHENTICATED, and cannot be made public. A Serverless
  cluster can only fail the logging dimension (Step 4). Do NOT apply
  Steps 1-3 to a Serverless cluster — it produces false positives. Check
  `ClusterType` first.

- **Public access requires the cluster to be in public subnets.**
  `PublicAccess.Type: SERVICE_PROVIDED_EIPS` attaches Elastic IPs to
  brokers. This only works if the broker subnets route to an Internet
  Gateway. A cluster in private subnets with public access enabled is a
  configuration error — MSK will accept the setting but the brokers
  remain unreachable from the internet. Still flag as PUBLIC_ACCESS
  because the intent (public exposure) is present even if the network
  topology doesn't complete the path.

- **`PublicAccess.Type: DISABLED` is NOT the absence of public access.**
  It is the explicit "off" state. An absent `ConnectivityInfo` block also
  means no public access. Both are safe — do not flag either as
  PUBLIC_ACCESS.

- **MSK encryption settings are immutable after creation.** Unlike
  EKS (which can toggle endpoint access with update-cluster-config), MSK
  cannot change `ClientBroker`, `InClusterEncryption`, or authentication
  modes after the cluster is created. Remediation for NO_ENCRYPTION or
  UNAUTHENTICATED requires creating a NEW cluster with the correct
  settings and migrating topics. State this explicitly in the
  remediation — operators often expect an in-place fix that does not
  exist.

- **SASL/SCRAM secrets live in AWS Secrets Manager with a mandated tag.**
  MSK discovers SCRAM credentials via secrets tagged
  `AmazonMSK_20181101`. A secret without this tag is invisible to MSK —
  clients configured for SCRAM fail with `SASL_AUTHENTICATION_FAILED`.
  When auditing SCRAM auth, verify the secret exists and has the tag, not
  just that `Sasl.Scram.enabled: true`.

- **mTLS requires an ACM Private Certificate Authority (PCA).** The
  `ClientAuthentication.Tls.CertificateAuthorityArnList` must reference a
  PCA ARN. A self-managed CA (uploaded as a truststore) is NOT supported
  on MSK Provisioned — only ACM PCA. The PCA costs ~$400/month; operators
  sometimes skip it and fall back to SASL only, which is valid but loses
  the mutual-identity guarantee of mTLS.

- **Broker logging destinations are independently toggleable.** MSK
  supports four log destinations: CloudWatch Logs, S3, Kinesis Data
  Firehose, and broker logs delivered to a specified destination. Each
  has its own `Enabled` flag. A cluster with only `S3.Enabled: true` and
  `CloudWatchLogs.Enabled: false` is logging — do NOT flag it as a
  logging gap. The requirement is at least ONE destination enabled.

- **Enhanced monitoring is separate from broker logging.**
  `EnhancedMonitoring: DEFAULT` controls the granularity of MSK metrics
  (broker-level vs per-topic-per-broker). It is a monitoring-level
  setting, not a security-forensic logging destination. Do NOT flag
  `EnhancedMonitoring: DEFAULT` as a logging gap — it is an operational
  advisory, not a CONFIG_GAP driver.

- **Open Monitoring (Prometheus) is a third-party integration layer.**
  `OpenMonitoring.Prometheus.JmxExporter.Enabled` or
  `NodeExporter.Enabled` controls Prometheus scrape endpoints. Missing
  Open Monitoring is NOT a logging gap — it is an observability choice.
  Do not confuse it with broker log delivery.

- **MSK configuration properties (auto.create.topics, unclean.leader.election)
  live in a separate describe-configuration call.** The `describe-cluster`
  output does NOT include Kafka broker properties. If the input includes
  configuration properties, audit them; if not, note that broker-level
  Kafka configuration was not provided and cannot be assessed (advisory,
  not a verdict driver).

- **`auto.create.topics.enable=true` is a silent privilege-escalation
  vector.** Any Kafka client can create topics with default replication
  and retention — including topics that capture sensitive data streams
  with no lifecycle policy. If the MSK configuration includes
  `auto.create.topics.enable=true`, flag it as a CONFIG_GAP finding
  regardless of the verdict.

- **`unclean.leader.election.enable=true` can cause data loss.** When a
  partition leader fails and no in-sync replica is available, an out-of-
  sync replica becomes leader, losing acknowledged messages. Flag as a
  CONFIG_GAP finding if present in the MSK configuration.

- **MSK does not support Security Groups on the cluster itself.** Broker
  security groups are attached to the broker ENIs (Elastic Network
  Interfaces), not to a cluster-level construct. They are found in
  `BrokerNodeGroupInfo.SecurityGroups` or queried via
  `aws ec2 describe-network-interfaces --filter Name=description,Values=MSK*`.
  A broker SG with `0.0.0.0/0` on port 9094 (TLS) or 9092 (plaintext)
  is an exposure — flag it as an additional CONFIG_GAP finding.

### Step 1: Encryption in-transit evaluation (NO_ENCRYPTION)

Examine `EncryptionInfo.EncryptionInTransit`:

1. If `ClientBroker` is `PLAINTEXT` → **NO_ENCRYPTION**. All
   client-to-broker traffic is unencrypted. Credentials (SASL/SCRAM),
   message payloads, and topic metadata are readable by anyone with a
   network tap on the path.

2. If `ClientBroker` is `TLS_PLAINTEXT` → **NO_ENCRYPTION**. Both TLS
   and plaintext listeners are active. A client connecting over the
   plaintext port sends everything unencrypted. The presence of a TLS
   option does not compensate for the plaintext path.

3. If `ClientBroker` is `TLS` → encryption-in-transit dimension passes
   for the client wire. Proceed to evaluate `InClusterEncryption`:
   - `InClusterEncryption: false` (or absent) → inter-broker traffic is
     plaintext. Note as a CONFIG_GAP finding (not NO_ENCRYPTION — the
     client wire is encrypted).
   - `InClusterEncryption: true` → full TLS in-transit. Dimension passes.

4. If `EncryptionInfo` or `EncryptionInTransit` is absent → treat as
   unknown encryption. Flag as CONFIG_GAP (cannot verify encryption
   posture from input).

### Step 2: Client authentication evaluation (UNAUTHENTICATED)

Examine `ClientAuthentication`:

1. If `Unauthenticated.Enabled: true` → **UNAUTHENTICATED**. Any client
   that can reach the broker TCP port can produce and consume without
   presenting credentials. This is the Kafka equivalent of an open
   database — the data is accessible to any network participant.

2. If `Unauthenticated.Enabled: false` (or `Unauthenticated` is absent)
   → authentication dimension passes. Note which auth modes are enabled:
   - `Tls.Enabled: true` → mTLS via ACM PCA (strongest — cryptographic
     client identity).
   - `Sasl.Iam.Enabled: true` → AWS IAM auth (strong — integrates with
     IAM policy governance).
   - `Sasl.Scram.Enabled: true` → SCRAM-SHA-512 via Secrets Manager
     (acceptable — credential-based, no IAM integration).

3. If NO authentication modes are enabled AND `Unauthenticated` is
   disabled or absent → the cluster accepts no clients. This is a
   misconfiguration — note as an ERROR advisory (not a security verdict).

### Step 3: Public access evaluation (PUBLIC_ACCESS)

Examine `BrokerNodeGroupInfo.ConnectivityInfo.PublicAccess`:

1. If `PublicAccess.Type` is `SERVICE_PROVIDED_EIPS` → **PUBLIC_ACCESS**.
   MSK attaches Elastic IPs to broker ENIs. Brokers are reachable from
   the internet on the client-facing ports (9092 for plaintext, 9094 for
   TLS). Even with TLS and authentication, this exposes the broker
   listener to global scanning, brute-force, and protocol-level CVE
   exploitation.

2. If `PublicAccess.Type` is `DISABLED` (or `ConnectivityInfo` / `PublicAccess`
   is absent) → no public access. Dimension passes.

3. If broker subnets are public (route table has `0.0.0.0/0` → IGW) but
   `PublicAccess` is `DISABLED` → brokers still have private IPs only.
   No PUBLIC_ACCESS, but note as an advisory finding (brokers in public
   subnets is an anti-pattern — they should be in private subnets for
   defense-in-depth).

### Step 4: Logging and encryption-at-rest evaluation (CONFIG_GAP)

This step covers two sub-dimensions. If EITHER triggers, the verdict is
CONFIG_GAP (assuming Steps 1-3 did not trigger).

#### 4a: Broker logging

Examine `LoggingInfo.BrokerLogs`:

1. If `LoggingInfo` is absent, or `BrokerLogs` is absent, or ALL
   destinations (`CloudWatchLogs`, `S3`, `Firehose`) have `Enabled: false`
   → **CONFIG_GAP**. No broker logs are being delivered. During an
   incident, you cannot reconstruct topic access, consumer group
   activity, or broker-level errors.

2. If at least ONE destination has `Enabled: true` → logging dimension
   passes. The cluster is delivering broker logs somewhere.

#### 4b: Encryption at-rest (KMS key governance)

Examine `EncryptionInfo.EncryptionAtRest.DataVolumeKMSKeyId`:

1. If `DataVolumeKMSKeyId` is absent, empty, or references an AWS-managed
   key (e.g., `alias/aws/kafka`) → **CONFIG_GAP**. Data is still
   encrypted (MSK always encrypts volumes), but key rotation, key policy,
   and decrypt-audit visibility are controlled by AWS, not the customer.

2. If `DataVolumeKMSKeyId` references a customer-managed CMK (a
   concrete key ARN or alias) → at-rest encryption dimension passes.

### Step 5: Aggregation — first match wins

The verdict is the **first matching condition** in priority order:

```text
if ClientBroker is PLAINTEXT or TLS_PLAINTEXT → verdict = NO_ENCRYPTION
elif Unauthenticated.Enabled: true            → verdict = UNAUTHENTICATED
elif PublicAccess.Type: SERVICE_PROVIDED_EIPS → verdict = PUBLIC_ACCESS
elif all logging disabled OR no CMK           → verdict = CONFIG_GAP
else                                          → verdict = OK
```

All triggered dimensions are listed as findings regardless of which
becomes the verdict.

## Output format (per cluster)

```text
CLUSTER: <cluster-name>
VERDICT: NO_ENCRYPTION | UNAUTHENTICATED | PUBLIC_ACCESS | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step 1)>
  - [CONFIG_GAP] <finding description (Step 4a/4b)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — plaintext with no logging

```text
CLUSTER: plaintext-broker
VERDICT: NO_ENCRYPTION
REASON: ClientBroker is PLAINTEXT — all client-to-broker traffic is
unencrypted (Step 1). Broker logging is also fully disabled (Step 4a).
FINDINGS:
  - [NO_ENCRYPTION] ClientBroker: PLAINTEXT — credentials and payloads
    transmitted in cleartext (Step 1)
  - [CONFIG_GAP] All broker log destinations disabled (Step 4a)
REMEDIATION:
  1. MSK encryption is immutable post-creation. Create a new cluster with
     ClientBroker: TLS and migrate topics. This is NOT an in-place fix.
  2. Enable broker logging on the replacement cluster:
     aws kafka update-broker-storage --cluster-arn <arn> # (no direct CLI for
     logging; use update-cluster-configuration or CloudFormation).
```

## Anti-Patterns — NEVER

- NEVER classify `ClientBroker: TLS_PLAINTEXT` as anything other than
  NO_ENCRYPTION. The plaintext listener is active — clients can and do
  connect without TLS. The existence of a TLS path does not compensate
  for the open plaintext path. This is the most common MSK
  misclassification.

- NEVER treat `ClientBroker: PLAINTEXT` as "acceptable if the VPC is
  private." VPC-level isolation is defense-in-depth, not a substitute
  for wire-level encryption. VPC traffic is interceptable by any
  compromised instance, peered network, or transit-gateway participant.
  Plaintext is always NO_ENCRYPTION regardless of network topology.

- NEVER apply Steps 1-3 (encryption, auth, public access) to an MSK
  Serverless cluster. Serverless enforces TLS + IAM auth and cannot be
  public. Applying Provisioned-audit logic produces false positives.
  Check `ClusterType: SERVERLESS` in the pre-flight gate and skip to
  Step 4.

- NEVER flag missing customer-managed KMS key as NO_ENCRYPTION. MSK
  ALWAYS encrypts data volumes at rest — the question is key governance
  (customer-managed vs AWS-managed), not encryption presence. Missing
  CMK is CONFIG_GAP, not NO_ENCRYPTION. Confusing the two produces
  false-critical alerts.

- NEVER assume `InClusterEncryption: false` is NO_ENCRYPTION. The
  client wire (`ClientBroker: TLS`) is still encrypted. Inter-broker
  plaintext is a CONFIG_GAP finding — the data crosses AZs unencrypted
  between brokers, but client-to-broker TLS is intact.

- NEVER classify `Unauthenticated.Enabled: true` as CONFIG_GAP. It is
  UNAUTHENTICATED — a separate, higher-priority verdict. Unauthenticated
  Kafka access means any network participant can read and write topics
  without credentials. This is not a "configuration gap" — it is an open
  data plane.

- NEVER classify `PublicAccess.Type: DISABLED` as PUBLIC_ACCESS. The
  `DISABLED` value is the explicit "off" state. An absent
  `ConnectivityInfo` block also means no public access. Both are safe.

- NEVER recommend changing `ClientBroker` from PLAINTEXT to TLS as an
  in-place operation. MSK encryption settings are immutable after
  cluster creation. The correct remediation is to create a new cluster
  with TLS enabled and migrate topics/consumer groups. Stating "enable
  TLS" without explaining the immutability constraint misleads operators.

- NEVER conflate broker logging with Enhanced Monitoring or Open
  Monitoring (Prometheus). `EnhancedMonitoring` controls metric
  granularity (DEFAULT / PER_BROKER / PER_TOPIC_PER_BROKER). Open
  Monitoring controls Prometheus scrape endpoints. Neither delivers
  broker log lines. The logging dimension checks
  `LoggingInfo.BrokerLogs` (CloudWatch / S3 / Firehose) only.

- NEVER assume the absence of `LoggingInfo` means logging is enabled.
  MSK defaults to NO broker logging on cluster creation. All four
  destinations start disabled. An absent `LoggingInfo` block means zero
  log delivery — classify as CONFIG_GAP.

- NEVER recommend SASL/SCRAM as equivalent to mTLS. SCRAM uses shared
  credentials stored in Secrets Manager — any client with the credential
  can impersonate any identity. mTLS binds the client identity to a
  certificate issued by a trusted PCA. SCRAM is acceptable; mTLS is
  stronger. State the trade-off, not a false equivalence.

- NEVER audit SCRAM auth without verifying the Secrets Manager secret
  exists and is tagged `AmazonMSK_20181101`. A cluster with
  `Sasl.Scram.Enabled: true` but no correctly tagged secret will fail
  all client connections with `SASL_AUTHENTICATION_FAILED`. The
  configuration says "SCRAM is on" but the credential store is empty —
  flag this as an operational ERROR, not a security verdict.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (update-cluster-configuration, broker storage update, cluster
  deletion), the auditor MUST emit:
  `CONFIRM: About to <action> on cluster <name> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Encryption immutability awareness.** Before recommending encryption
  remediation, verify the operator understands that MSK encryption
  settings CANNOT be changed in-place. The remediation path is: create
  new cluster with TLS → mirror topics → validate → cut over consumers
  → decommission old cluster. This is a multi-day operation, not a
  one-line CLI fix.

- **Public access toggle blast radius.** Disabling public access
  (`PublicAccess.Type: DISABLED`) immediately breaks all clients
  connecting via the Elastic IPs. Verify VPN/Direct Connect/bastion
  connectivity BEFORE the change.

- **Logging enablement cost.** Enabling broker log delivery to
  CloudWatch creates log groups with ingestion charges. A busy MSK
  cluster with many partitions generates significant broker log volume.
  Estimate volume first and set a retention policy:
  `aws logs put-retention-policy --log-group-name <name>
  --retention-in-days 90`.

- **Configuration change propagation.** MSK configuration changes
  (update-cluster-configuration) trigger a rolling broker restart. The
  cluster remains available (other brokers serve traffic), but
  partition leadership shifts during the rollout. Schedule during a
  maintenance window.

## Remediation guidance

### For NO_ENCRYPTION — ClientBroker PLAINTEXT or TLS_PLAINTEXT

1. MSK encryption settings are **immutable**. You cannot change
   `ClientBroker` on an existing cluster. The remediation is:
   - Create a new cluster with `ClientBroker: TLS` and
     `InClusterEncryption: true`.
   - Mirror topics using MirrorMaker 2 or MSK Replicator.
   - Validate consumer group offsets on the new cluster.
   - Cut over producers and consumers.
   - Decommission the old cluster.

2. Example CloudFormation snippet for the replacement cluster:
   ```yaml
   EncryptionInfo:
     EncryptionInTransit:
       ClientBroker: TLS
       InClusterEncryption: true
   ```

3. If regulatory constraints require immediate cessation of plaintext
   traffic, restrict the broker security group to deny inbound on port
   9092 (plaintext) as an interim control while the migration proceeds.

### For UNAUTHENTICATED — unauthenticated clients enabled

1. Disable unauthenticated access via MSK configuration. Note: this
   requires a cluster configuration update and broker rolling restart:
   ```bash
   # The client-authentication settings are part of the cluster's
   # security configuration and may require cluster recreation on
   # older MSK versions. On MSK 2.7.1+, update via:
   aws kafka update-security --cluster-arn <arn> \
     --client-authentication '{"unauthenticated": {"enabled": false}}'
   ```

2. Verify at least one auth mode (TLS, SASL/IAM, or SASL/SCRAM) remains
   enabled BEFORE disabling unauthenticated. Locking out all clients is
   an instant outage.

### For PUBLIC_ACCESS — brokers exposed via Elastic IPs

1. Disable public access:
   ```bash
   aws kafka update-connectivity --cluster-arn <arn> \
     --connectivity-info '{"publicAccess": {"type": "DISABLED"}}'
   ```

2. Verify VPN, Direct Connect, or VPC peering provides client access
   BEFORE disabling. All clients using the Elastic IP endpoints will
   lose connectivity immediately.

3. Verify the change:
   ```bash
   aws kafka describe-cluster --cluster-arn <arn> \
     --query 'clusterInfo.brokerNodeGroupInfo.connectivityInfo.publicAccess'
   ```

### For CONFIG_GAP — broker logging disabled

1. Enable at least one log destination (CloudWatch recommended for
   operational visibility):
   ```bash
   aws kafka update-broker-storage --cluster-arn <arn>  # logging requires
   # update-cluster-configuration or the console; CLI support varies by
   # MSK API version. Use CloudFormation or the AWS Console for logging
   # updates.
   ```

2. Set a retention policy on the log group:
   ```bash
   aws logs put-retention-policy \
     --log-group-name /aws/kafka/cluster-<id> \
     --retention-in-days 90
   ```

### For CONFIG_GAP — no customer-managed KMS key

1. Create a customer-managed KMS key with a restrictive policy.
2. This requires cluster recreation (at-rest encryption key is
   immutable post-creation). Plan a migration similar to the
   NO_ENCRYPTION remediation.
3. On the new cluster, specify:
   ```yaml
   EncryptionInfo:
     EncryptionAtRest:
       DataVolumeKMSKeyId: arn:aws:kms:us-east-1:111111111111:key/<cmk-id>
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit (quarterly) as Kafka versions and MSK
   features evolve.
3. Consider enabling Open Monitoring (Prometheus) for deeper operational
   visibility if not already configured.
4. Verify the MSK configuration properties do not include
   `auto.create.topics.enable=true` or
   `unclean.leader.election.enable=true` (these are not visible in
   describe-cluster output — fetch separately with
   `aws kafka describe-configuration`).

## Recent AWS features (2024-2026)

- **MSK Serverless GA (2024):** MSK Serverless auto-scales capacity without managing brokers. Auditors should note that MSK Serverless changes the audit surface — there are no broker instances to audit (no broker public access, no per-broker logging). Instead, verify the serverless cluster's VPC configuration, IAM/TLS authentication, and Kafka version compatibility.
- **MSK Connect updates (2024-2025):** Enhanced MSK Connect with more connector types and improved error handling. Auditors should verify that MSK Connect worker configurations use encrypted connections and that connector logs are enabled.
- **KRaft mode (2024-2025):** MSK now supports KRaft (Kafka Raft) mode, eliminating the ZooKeeper dependency. Auditors should verify that KRaft-mode clusters have appropriate monitoring — ZooKeeper-specific metrics no longer apply.
- **IAM authentication enhancements (2024):** Expanded IAM auth support for Kafka client connections. Auditors should verify that clusters enforce IAM or TLS client authentication and that `unauthenticated` access is disabled.

## Domain

AWS CloudOps / MSK Analytics Security & Compliance.
