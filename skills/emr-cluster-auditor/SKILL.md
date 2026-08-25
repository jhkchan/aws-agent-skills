---
name: emr-cluster-auditor
description: Audits AWS EMR clusters for security configuration across three encryption layers (S3 at-rest, local-disk at-rest, in-transit TLS), IAM roles (service, EC2 instance profile, AutoScaling), Kerberos authentication, block public access, debug logging, and instance-group posture. Emits a deterministic verdict (NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK) per cluster with enumerated findings and specific remediation. Use when reviewing EMR clusters for encryption gaps, over-permissive roles, Kerberos coverage, block-public-access state, or hardening before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline config-document classification. Live-account audits use aws emr describe-cluster, aws emr describe-security-configuration, aws emr get-block-public-access-configuration, and aws iam list-attached-role-policies (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  verdict_shape: NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
  when_to_use: Reviewing an EMR cluster configuration before production deployment, checking for encryption gaps (S3, local disk, in-transit), auditing IAM roles attached to the cluster, validating Kerberos authentication, checking block-public-access posture, or hardening EMR security configuration.
  activation_triggers: audit this EMR cluster, check EMR encryption, is my EMR cluster encrypted, EMR security configuration, EMR IAM role too permissive, Kerberos EMR, block public access EMR, harden EMR cluster, EMR local disk encryption, EMR in-transit encryption
  invocation_schema: 'Input: either (a) an EMR cluster configuration (describe-cluster output + describe-security-configuration output + IAM role policies), OR (b) a cluster-id for live-account audit. Output: deterministic CLUSTER/VERDICT/REASON/FINDINGS/REMEDIATION block per cluster, where VERDICT ∈ {NO_ENCRYPTION, OVERPERMISSIVE_ROLE, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EMR, EMR encryption, in-transit encryption, S3 SSE-KMS, local disk encryption, LUKS, SecurityConfiguration, Kerberos, block public access, instance profile role, EMR service role, AutoScaling role, iam:PassRole, debug logging, EMR audit, data-at-rest, data-in-transit, Spark, Hive, instance group, Hadoop
  tags: emr, security, encryption, iam-roles, kerberos, analytics, audit, compliance
---

# EMR Cluster Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across all
dimensions, and the SecurityConfiguration is the single source of truth for
encryption — but `describe-cluster` only returns its **name**, not its
contents. An audit that does not fetch and parse the SecurityConfiguration
misses every encryption finding.

EMR clusters process large datasets across distributed nodes — the data flows
through three distinct planes, each with its own encryption surface:
- **S3 at-rest** — data read from and written to S3 (input, output, logs).
- **Local-disk at-rest** — intermediate data on EBS volumes and instance-store
  ephemeral disks (Spark shuffle, HDFS blocks, temp files).
- **In-transit** — inter-node RPC, Spark shuffle, HTTP, and Hadoop
  communication across the cluster network.

If any plane is unencrypted, the data is exposed at that layer. A cluster with
in-transit encryption but no local-disk encryption still writes shuffle
partitions in plaintext to EBS volumes — readable by any co-located tenant or
volume-snapshot attacker.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| No SecurityConfiguration attached | **NO_ENCRYPTION** | 1a |
| SecurityConfiguration missing InTransitEncryptionConfiguration | **NO_ENCRYPTION** | 1b |
| SecurityConfiguration missing S3EncryptionConfiguration | **NO_ENCRYPTION** | 1c |
| SecurityConfiguration missing LocalDiskEncryptionConfiguration | **NO_ENCRYPTION** | 1d |
| EC2 instance profile role with `Action: "*"` on `Resource: "*"` | **OVERPERMISSIVE_ROLE** | 2a |
| EC2 role or service role with service wildcard on `"*"` (e.g., `s3:*`) | **OVERPERMISSIVE_ROLE** | 2b |
| Any role with `iam:PassRole` on `"*"` | **OVERPERMISSIVE_ROLE** | 2c |
| Debug logging disabled | **CONFIG_GAP** | 3a |
| Block Public Access not set to BLOCK | **CONFIG_GAP** | 3b |
| Kerberos authentication not enabled | **CONFIG_GAP** | 3c |
| All encryption + scoped roles + complete config | **OK** | 4 |

Verdict precedence: **NO_ENCRYPTION > OVERPERMISSIVE_ROLE > CONFIG_GAP > OK**.

## Pre-flight: cluster metadata gate

Before evaluating encryption and roles, classify the cluster itself. Several
attributes short-circuit or redirect the audit.

| Attribute | Effect |
|---|---|
| `SecurityConfiguration` field absent on describe-cluster | No security configuration attached — jump to Step 1a. All three encryption layers are absent by definition. |
| `SecurityConfiguration` field present (name only) | You MUST call `describe-security-configuration --name <name>` to get the actual encryption settings. The cluster metadata only returns the config name string, not the parsed object. |
| `ReleaseLabel` < `emr-5.31.0` | In-transit encryption may not be supported on older release labels. Flag as CONFIG_GAP even if the SecurityConfiguration references it — the feature may silently fail on incompatible releases. |
| `KerberosAttributes` absent | No Kerberos authentication — cluster relies solely on IAM for access control. Flag as CONFIG_GAP (Step 3c). |
| `LogUri` absent | Debug logging cannot be enabled without a LogUri. If `--enable-debugging` is true but LogUri is absent, the logs go nowhere. |
| `VisibleToAllUsers: true` | Deprecated flag — cluster is visible to all IAM users in the account. Flag as a CONFIG_GAP finding (Step 3). |

**If the input does not include the SecurityConfiguration contents** (only the
cluster metadata), output:

```text
CLUSTER: <cluster-id>
VERDICT: ERROR
REASON: SecurityConfiguration contents not provided. The cluster metadata only
contains the config name — retrieve the parsed encryption settings with
`aws emr describe-security-configuration --name <name> --profile <p>` and re-audit.
REMEDIATION: Fetch the security configuration and re-run the audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious EMR behaviors that change classification

These behaviors are easy to misjudge without operational EMR experience. Each
changes a verdict if ignored:

- **describe-cluster returns the config NAME, not the contents.** The
  `SecurityConfiguration` field on the cluster object is a string like
  `"my-sec-config"`. The actual encryption settings live in a separate API
  call: `aws emr describe-security-configuration --name my-sec-config`. The
  output's `SecurityConfiguration` field is itself a **JSON string** (double-
  serialized) — you must parse it twice. An audit that reads only the cluster
  metadata cannot evaluate encryption at all.

- **In-transit encryption distributes a PEM certificate to all nodes.** The
  `InTransitEncryptionConfiguration.TLSCertificateConfiguration` requires a
  certificate chain AND private key stored in S3 (`S3Object` field) or
  provisioned via a custom provider. EMR does NOT auto-generate TLS certs. If
  the certificate expires, inter-node TLS silently breaks and some services
  fall back to plaintext. EMR does not monitor certificate expiry.

- **S3 encryption via SSE-KMS vs CSE-KMS have different threat models.**
  SSE-KMS: the S3 service encrypts at write time using a KMS key — the EC2
  instance profile needs `kms:GenerateDataKey*` and `kms:Decrypt`. CSE-KMS:
  the EMR client-side SDK encrypts BEFORE upload — stronger (data never
  leaves the node in plaintext) but adds CPU overhead and requires the
  `EncryptionMode` to be `CSE-KMS`. Both are valid; `SSE-S3` (AES-256 with
  AWS-managed keys) provides no granular key control and should be flagged as
  a weaker option.

- **Local-disk encryption uses LUKS for instance stores and EBS encryption for
  EBS volumes.** These are separate mechanisms. The
  `LocalDiskEncryptionConfiguration` with `EncryptionKeyProviderType: AwsKms`
  uses a KMS key to generate a LUKS passphrase that encrypts instance-store
  ephemeral disks. EBS volumes are encrypted via EBS encryption (separate
  account-level setting). If `LocalDiskEncryptionConfiguration` is absent,
  instance-store data (Spark shuffle, HDFS replicas) is plaintext even if EBS
  encryption is enabled at the account level.

- **Block Public Access is a REGION-level setting, not per-cluster.**
  `aws emr get-block-public-access-configuration` returns the region-wide
  policy. `BlockPublicSecurityGroupRules: true` blocks clusters from having
  security groups with 0.0.0.0/0 inbound rules. The default is PERMIT — public
  access is allowed unless explicitly blocked. A cluster in a region where BPA
  is not configured has no network-level guardrail against public exposure.

- **The EC2 instance profile is the DATA-PROCESSING identity.** The
  `Ec2InstanceAttributes.IamInstanceProfile` role is assumed by every EC2
  instance in the cluster. It reads input data from S3, writes output, and
  accesses KMS for encryption. Over-permissioning this role is the most common
  EMR security issue — it should have scoped `s3:Get*`/`s3:Put*`/`s3:List*`
  on specific bucket ARNs, not `s3:*` on `*`.

- **The EMR service role manages cluster lifecycle, not data.** The
  `ServiceRole` provisions EC2 instances, writes logs to S3, and manages
  instance groups. The default `EMR_DefaultRole` has the
  `AmazonElasticMapReduceRole` managed policy, which includes
  `elasticmapreduce:*` and broad `s3:Get*`/`s3:List*` — this is the AWS
  default and acceptable, but a custom service role with `Action: "*"` is
  OVERPERMISSIVE_ROLE.

- **SecurityConfiguration cannot be modified on a running cluster.** Changing
  encryption settings requires terminating and recreating the cluster with a
  new SecurityConfiguration. This is a one-way door — always back up the
  current configuration before remediation.

- **Debug logging writes detailed cluster configuration to S3.** When enabled
  (`--enable-debugging`), EMR writes Hadoop, Spark, and application logs to the
  LogUri S3 bucket. If the bucket is unencrypted or cross-account, these logs
  expose job configurations, intermediate data paths, and potentially secrets
  passed via bootstrap actions. Always verify the LogUri bucket has SSE-KMS.

- **Kerberos dedicated KDC is ephemeral.** When `KerberosAttributes.Provider:
  ClusterDedicatedKdc`, the KDC runs on the master node and dies when the
  cluster terminates. For persistent auth across cluster lifecycles, use
  `ExternalKdc`. A dedicated KDC also means a single point of failure — if
  the master node restarts, all Kerberos tickets are invalidated.

- **AutoScaling role can chain to PassRole.** The `AutoScalingRole`
  (`EMR_AutoScaling_DefaultRole`) includes `iam:PassRole` to pass the EC2
  instance profile to newly scaled instances. If scoped to `Resource: "*"`,
  it can pass ANY role — a privilege-escalation vector.

### Step 1: Encryption gate — NO_ENCRYPTION (highest priority)

Evaluate the SecurityConfiguration for all three encryption layers. Any missing
layer produces NO_ENCRYPTION — the data is exposed at that plane.

**Step 1a: No SecurityConfiguration attached.** If the cluster metadata has
no `SecurityConfiguration` field, ALL three layers are absent. This is the
worst case — S3 data, local disks, and inter-node traffic are all plaintext.

**Step 1b: InTransitEncryptionConfiguration absent or empty.** Inter-node
communication (Spark shuffle, Hadoop RPC, HDFS data transfer) is plaintext.
Any co-located tenant or network MITM can read the data stream. This is
NO_ENCRYPTION.

**Step 1c: AtRestEncryptionConfiguration.S3EncryptionConfiguration absent or
empty.** Data written to S3 (output, logs, EMRFS objects) is plaintext. This
exposes the full dataset to anyone with S3 read access. NO_ENCRYPTION.

**Step 1d: AtRestEncryptionConfiguration.LocalDiskEncryptionConfiguration
absent or empty.** Instance-store ephemeral disks (Spark shuffle partitions,
HDFS blocks) and EBS volumes are plaintext. Data is readable by volume-snapshot
attackers or co-located tenants. NO_ENCRYPTION.

If all three layers are present and correctly configured, proceed to Step 2.

**Encryption mode assessment (informational, does not change verdict):** If
S3Encryption uses `SSE-S3` instead of `SSE-KMS` or `CSE-KMS`, note it as a
weaker option (AWS-managed keys, no granular access control, no CloudTrail
per-key audit). This is an additive FINDINGS note, not a verdict driver.

### Step 2: IAM role audit — OVERPERMISSIVE_ROLE

If encryption passes (Step 1), evaluate the three EMR roles for
over-permissioning. The verdict is OVERPERMISSIVE_ROLE if any role has
wildcard or escalation patterns.

**Step 2a: Admin wildcard.** Any role with `Action: "*"` on `Resource: "*"`
→ OVERPERMISSIVE_ROLE. This grants administrative access to every service and
resource in the account.

**Step 2b: Service wildcard on all resources.** Any role with a service-level
wildcard (e.g., `s3:*`, `ec2:*`, `kms:*`) on `Resource: "*"` →
OVERPERMISSIVE_ROLE. The EC2 instance profile is the most common offender —
`s3:*` on `*` grants read/write/delete on every bucket in the account.

**Step 2c: Privilege escalation.** Any role with `iam:PassRole` on
`Resource: "*"` → OVERPERMISSIVE_ROLE. The PassRole vector lets the caller
pass any role to EC2, Lambda, or any service — executing under the passed
role's permissions. For the EMR AutoScaling role, this is especially dangerous:
it can inject a different instance profile into scaled instances.

**Default managed policy exception:** The `AmazonElasticMapReduceRole`
(service role default) and `AmazonElasticMapReduceforEC2Role` (EC2 profile
default) are AWS-managed policies with broad but service-scoped permissions.
These are the AWS defaults — flag them as MEDIUM FINDINGS notes (recommend
scoping to specific bucket ARNs) but do NOT trigger OVERPERMISSIVE_ROLE unless
a custom inline policy adds wildcards.

**`kms:Decrypt` on `"*"` exception:** If the EC2 instance profile role grants
`kms:Decrypt` on `Resource: "*"`, this is OVERPERMISSIVE_ROLE — it is a
silent data-exfiltration multiplier (same logic as the KMS auditor). Scope to
the specific key ARNs used by the SecurityConfiguration.

### Step 3: Configuration completeness — CONFIG_GAP

If encryption and roles pass (Steps 1-2), evaluate configuration completeness.
Multiple dimensions may produce additive CONFIG_GAP findings.

**Step 3a: Debug logging.** If debug logging is disabled (no `LogUri`, or
`--enable-debugging` not set), the cluster has no observability for
troubleshooting. More importantly, when enabled, verify the LogUri S3 bucket
has SSE-KMS encryption — unencrypted debug logs expose cluster internals.
Disabled debug logging is a CONFIG_GAP (operational risk).

**Step 3b: Block Public Access.** If the region-level Block Public Access is
not configured (defaults to PERMIT), the cluster has no guardrail against
public security group rules. If `BlockPublicSecurityGroupRules` is `false`
or the configuration is absent, this is CONFIG_GAP.

**Step 3c: Kerberos authentication.** If `KerberosAttributes` is absent,
the cluster has no authentication layer beyond IAM. Any principal with EMR
permissions can submit jobs and access data. For clusters processing sensitive
data (PII, financial), Kerberos is a hardening requirement. Flag as CONFIG_GAP.

**Step 3d: Single master (no HA).** If the MASTER instance group has
`RequestedInstanceCount: 1`, there is no master redundancy. A master failure
terminates the cluster. This is primarily an availability risk but is flagged
as CONFIG_GAP for production clusters.

**Step 3e: VisibleToAllUsers.** If `VisibleToAllUsers: true`, any IAM user in
the account can see and modify the cluster. This is a deprecated flag — flag
as CONFIG_GAP.

### Step 4: Aggregation — worst verdict wins

The final verdict is the **maximum severity** across all findings, where
NO_ENCRYPTION > OVERPERMISSIVE_ROLE > CONFIG_GAP > OK:

```text
verdict = max(encryption_verdict, role_verdict, config_verdict)
```

If no findings (all dimensions pass), the verdict is **OK**.

## Output format (per cluster)

```text
CLUSTER: <cluster-id or name>
VERDICT: NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step Na)>
  - [CONFIG_GAP] <finding description (Step Nb)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — over-permissive EC2 role with encryption present

```text
CLUSTER: j-OVERPERMISSIVE-EC2-ROLE
VERDICT: OVERPERMISSIVE_ROLE
REASON: EC2 instance profile role "EMR_EC2_CustomRole" grants s3:* on Resource
"*" (Step 2b) — the data-processing identity has uncontrolled S3 access across
every bucket in the account.
FINDINGS:
  - [OVERPERMISSIVE_ROLE] EC2 role s3:* on "*" — unrestricted S3 read/write/delete
    on all buckets (Step 2b)
  - [OK] All three encryption layers present and configured with SSE-KMS
  - [CONFIG_GAP] Kerberos authentication not enabled (Step 3c)
REMEDIATION:
  1. Scope the EC2 instance profile S3 permissions to specific bucket ARNs
     (s3:GetObject, s3:PutObject, s3:ListBucket on arn:aws:s3:::emr-input/*).
  2. Enable Kerberos for sensitive-data clusters.
```

## Anti-Patterns — NEVER

- NEVER assume encryption is enabled just because a SecurityConfiguration name
  is attached. The name is a pointer — you must fetch and parse the actual
  configuration via `describe-security-configuration`. An audit that stops at
  `describe-cluster` misses every encryption finding.

- NEVER classify a cluster as OK when any of the three encryption layers is
  absent. A cluster with in-transit encryption but no local-disk encryption
  still writes Spark shuffle data in plaintext to EBS volumes. Partial
  encryption is NO_ENCRYPTION, not OK.

- NEVER recommend replacing SSE-KMS or CSE-KMS with SSE-S3 as remediation.
  SSE-S3 uses AWS-managed keys with no per-key access control, no CloudTrail
  per-key audit, and no cross-account key policy. It is a downgrade, not a
  simplification.

- NEVER attempt to modify the SecurityConfiguration on a running cluster.
  Encryption settings are immutable after cluster creation — you must
  terminate and recreate with a new configuration. Always capture the current
  configuration for rollback before remediation.

- NEVER overlook the EC2 instance profile role. It is the DATA-PROCESSING
  identity — it reads every S3 object the cluster processes, accesses every
  KMS key used for encryption, and runs every line of Spark/Hive code.
  Over-permissioning here is the most common EMR security issue.

- NEVER treat `iam:PassRole` on `"*"` in the AutoScaling role as a minor issue.
  The AutoScaling role provisions new instances — if it can pass ANY role,
  an attacker can inject a privileged instance profile into scaled nodes,
  escalating beyond the original EC2 role.

- NEVER assume Block Public Access is enabled by default. The EMR BPA setting
  defaults to PERMIT (public access allowed). It must be explicitly set to
  BLOCK at the region level. A cluster in an unconfigured region has no
  network-level guardrail.

- NEVER treat debug logging as purely operational. Debug logs contain Hadoop
  configuration XMLs, Spark job graphs, and application stderr/stdout. If the
  LogUri S3 bucket is unencrypted or cross-account, these logs expose cluster
  internals and potentially bootstrap-action secrets.

- NEVER classify the default `AmazonElasticMapReduceRole` managed policy as
  OVERPERMISSIVE_ROLE by itself. It is the AWS default with broad but
  service-scoped permissions. Flag it as a MEDIUM finding recommending
  scoping — do not trigger the verdict unless a custom inline policy adds
  wildcards.

- NEVER ignore the release label when evaluating encryption compatibility.
  In-transit encryption requires `emr-5.31.0+`; local-disk encryption requires
  `emr-5.26.0+`. A SecurityConfiguration referencing unsupported features on
  an older release label silently fails — the cluster starts without
  encryption and reports no error.

- NEVER assume a dedicated Kerberos KDC provides persistent authentication.
  The dedicated KDC runs on the master node — when the cluster terminates,
  all Kerberos principals and tickets are destroyed. For cross-cluster or
  persistent auth, use an external KDC.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any destructive or state-changing
  operation (terminating a cluster, modifying BPA, detaching a role), emit:
  `CONFIRM: About to <action> on cluster <id> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`
- **SecurityConfiguration changes require cluster recreation.** You cannot
  modify encryption settings on a running cluster. The safe procedure is:
  (1) capture current config, (2) create a new SecurityConfiguration with the
  fixed settings, (3) launch a replacement cluster with the new config, (4)
  migrate workloads, (5) terminate the old cluster only after validation.
- **IAM role changes are near-instant.** Detaching or attaching a managed
  policy takes effect within seconds. But a running cluster may cache the
  instance-profile credentials for up to 1 hour (EC2 metadata refresh
  interval). Plan for a credential-refresh delay when tightening permissions.
- Before tightening the EC2 instance profile S3 permissions, verify the
  workload's bucket dependencies (input, output, logs, bootstrap scripts).
  Overtightening breaks running jobs with `AccessDenied`.
- Prefer additive changes (attach a tighter managed policy, add a Deny
  statement) over destructive changes (detach the existing role) — additive
  changes are reversible and do not risk breaking the cluster.

## Remediation guidance

### For NO_ENCRYPTION

1. **Create or update a SecurityConfiguration** with all three encryption
   layers:
   ```bash
   aws emr create-security-configuration \
     --name hardened-config \
     --security-configuration '{"EncryptionConfiguration":{"AtRestEncryptionConfiguration":{"S3EncryptionConfiguration":{"EncryptionMode":"SSE-KMS","AwsKmsKey":"arn:aws:kms:us-east-1:111111111111:key/abc"},"LocalDiskEncryptionConfiguration":{"EncryptionKeyProviderType":"AwsKms","AwsKmsKey":"arn:aws:kms:us-east-1:111111111111:key/def"}},"InTransitEncryptionConfiguration":{"TLSCertificateConfiguration":{"CertificateProviderType":"PEM","S3Object":"s3://certs/certchain.pem"}}}}'
   ```
2. **Terminate and recreate the cluster** with the new SecurityConfiguration.
   SecurityConfiguration is immutable after creation.
3. **Verify the KMS key policy** grants the EC2 instance profile
   `kms:GenerateDataKey*` and `kms:Decrypt` on the encryption keys.
4. For the in-transit TLS certificate, ensure it is not expired and the CN
   matches the cluster domain.

### For OVERPERMISSIVE_ROLE

1. **Scope the EC2 instance profile** to specific bucket ARNs:
   ```bash
   aws iam put-role-policy --role-name EMR_EC2_CustomRole \
     --policy-name scoped-s3-access \
     --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetObject","s3:ListBucket"],"Resource":["arn:aws:s3:::emr-input","arn:aws:s3:::emr-input/*"]},{"Effect":"Allow","Action":["s3:PutObject"],"Resource":["arn:aws:s3:::emr-output/*"]}]}'
   ```
2. **Remove `iam:PassRole` on `"*"`** from the AutoScaling role — scope to the
   specific EC2 instance profile ARN only.
3. **For `kms:Decrypt` on `"*"`**: scope to the specific KMS key ARNs used by
   the SecurityConfiguration.

### For CONFIG_GAP

1. **Enable debug logging:**
   ```bash
   aws emr put-auto-termination-policy --cluster-id <id> --auto-termination-policy ...
   # Debug logging is set at cluster creation: --enable-debugging --log-uri s3://...
   ```
2. **Enable Block Public Access:**
   ```bash
   aws emr put-block-public-access-configuration \
     --block-public-access-configuration '{"BlockPublicSecurityGroupRules":true,"PermittedPublicSecurityGroupRuleRanges":[{"MinRange":0,"MaxRange":65535}]}'
   ```
   Note: setting `PermittedPublicSecurityGroupRuleRanges` to the full range
   effectively blocks nothing — set it to an empty array to block all public
   rules, or to specific ports (e.g., 22 for SSH from known CIDRs only).
3. **Enable Kerberos** (requires cluster recreation):
   ```bash
   aws emr create-cluster --kerberos-attributes '{"Realm":"EXAMPLE.COM","KdcAdminPassword":"...","Provider":"ClusterDedicatedKdc"}'
   ```

### For OK

1. No remediation required.
2. Recommend periodic certificate-expiry checks for the in-transit TLS cert.
3. Recommend scoping the default managed policies to specific bucket ARNs as
   defense-in-depth.

## Recent AWS features (2024-2026)

- **EMR Serverless GA and enhanced (2024-2025):** EMR Serverless allows running Spark/Hive applications without managing clusters. Auditors should note that EMR Serverless changes the audit surface — there is no EC2 instance group or security group to audit. Instead, verify the EMR Serverless application's VPC configuration, KMS encryption, and execution role.
- **EMR on EKS updates (2024):** Enhanced EMR on EKS with Spark 3.5 support and improved pod-level IAM. Auditors should verify that the EMR execution role on EKS is scoped to the namespace and that Spark UI access is authenticated.
- **EMR managed scaling improvements (2024-2025):** Improved managed scaling with spot instance diversification. No new audit-surface fields, but auditors should verify that the managed scaling policy does not create single-AZ concentration.

## Domain

AWS CloudOps / EMR Analytics Security & Compliance.

## AWS documentation

- **Amazon EMR Management Guide** — https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-what-is-emr.html
- **EMR Security** — https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-security.html
- **EMR API Reference** — https://docs.aws.amazon.com/emr/latest/APIReference/
- **AWS CLI Reference for EMR** — https://docs.aws.amazon.com/cli/latest/reference/emr/
- **EMR Serverless** — https://docs.aws.amazon.com/emr/latest/Serverless.html
