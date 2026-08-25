---
name: redshift-cluster-auditor
description: Audits Amazon Redshift provisioned clusters for security posture and configuration gaps — public accessibility (internet-exposed cluster), KMS encryption-at-rest (immutable post-creation), require_ssl parameter group enforcement, S3 audit logging, VPC security-group ingress on the cluster port, automated-snapshot retention (PITR), and enhanced VPC routing (COPY/UNLOAD traffic path). Emits a deterministic categorical verdict (PUBLIC | NO_ENCRYPTION | NO_SSL | NO_AUDIT_LOG | CONFIG_GAP | OK) per cluster with enumerated findings and specific remediation. Use when reviewing a Redshift cluster before production deployment, auditing encryption or SSL posture, checking S3 audit logging coverage, validating snapshot retention, or hardening data-warehouse security.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline metadata classification. Live-account audits use aws redshift describe-clusters, describe-logging-status, describe-cluster-parameter-groups (with describe-cluster-parameters for the PG), aws ec2 describe-security-groups, and aws kms describe-key (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  verdict_shape: PUBLIC | NO_ENCRYPTION | NO_SSL | NO_AUDIT_LOG | CONFIG_GAP | OK
  when_to_use: Reviewing a Redshift provisioned cluster before production deployment, auditing encryption-at-rest, validating require_ssl enforcement, checking S3 audit logging coverage, inspecting automated-snapshot retention, evaluating enhanced VPC routing posture, or hardening a data warehouse for a compliance review.
  activation_triggers: audit this Redshift cluster, is my Redshift cluster public, is encryption enabled on Redshift, is require_ssl on, is Redshift audit logging configured, are automated snapshots enabled, enhanced VPC routing Redshift, Redshift security group audit, harden this data warehouse
  invocation_schema: 'Input: either (a) a describe-clusters Cluster block, optionally paired with describe-logging-status, describe-cluster-parameters (for the attached parameter group), and describe-security-groups outputs, OR (b) a ClusterIdentifier for live-account audit. Output: deterministic CLUSTER/VERDICT/REASON/FINDINGS/REMEDIATION block per cluster, where VERDICT ∈ {PUBLIC, NO_ENCRYPTION, NO_SSL, NO_AUDIT_LOG, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Redshift, data warehouse, PubliclyAccessible, encryption, KMS, require_ssl, SSL, TLS, parameter group, audit logging, S3 audit log, enable_user_activity_logging, automated snapshots, AutomatedSnapshotRetentionPeriod, enhanced VPC routing, EnhancedVPCRouting, COPY, UNLOAD, VPC security group, cluster port 5439, data-warehouse hardening, compliance, Redshift Serverless
  tags: redshift, analytics, security, encryption, ssl, audit-logging, snapshots, vpc, compliance, audit
---

# Redshift Cluster Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
six ordered dimensions, and `PubliclyAccessible: true` on a Redshift
cluster is in a class of its own — it places a petabyte-scale data
warehouse on the public internet with no VPC boundary in front of it.

Redshift clusters concentrate an organisation's most sensitive analytics
data: customer records, financial transactions, product analytics. Three
Redshift-specific behaviours drive the classification:

- **`PubliclyAccessible: true` is a direct internet endpoint.** Unlike RDS
  (where the SG + PubliclyAccessible + subnet routing combine), Redshift
  with `PubliclyAccessible: true` is reachable from `0.0.0.0/0` over TCP
  5439 (or 5440). There is no "public subnet routing" subtlety — the flag
  is the exposure. A public Redshift cluster is a public data warehouse.
- **Encryption-at-rest is immutable per cluster.** Unlike RDS or EBS,
  there is no online modify flow and no snapshot-restore toggle. The
  *only* path is: provision a new encrypted cluster, `UNLOAD` from the
  old, `COPY` into the new, redirect downstream BI tools, decommission
  the old. Treat `Encrypted: false` as a migration backlog, not a CLI
  toggle.
- **`require_ssl` lives in the parameter group, not the cluster metadata.**
  The default value is `false` and the default parameter group
  (`default.redshift-1.0`) cannot be modified — a cluster on the default
  PG is reporting the engine default, not an operator decision. The
  parameter must be set to `true` in a *custom* parameter group, and the
  cluster must be rebooted for the change to apply.

## Quick reference — verdict priority

| Condition | Verdict | Step |
|---|---|---|
| `PubliclyAccessible: true` | **PUBLIC** | Step 1 |
| `Encrypted: false` | **NO_ENCRYPTION** | Step 2 |
| `require_ssl` parameter value is `false` (or unset) | **NO_SSL** | Step 3 |
| `LoggingEnabled: false` (describe-logging-status) | **NO_AUDIT_LOG** | Step 4 |
| Any of: snapshot retention 0, enhanced VPC routing off, SG ingress `0.0.0.0/0` on cluster port | **CONFIG_GAP** | Step 5 |
| All dimensions pass | **OK** | Step 6 |

Apply in order; the first matching verdict wins. The ordering is
deliberate: PUBLIC > NO_ENCRYPTION > NO_SSL > NO_AUDIT_LOG > CONFIG_GAP > OK.
All findings still appear in the FINDINGS list regardless of which one
became the verdict. See the ordered steps below for Redshift-specific edge
cases (AWS-managed vs customer-managed KMS, default vs custom parameter
group, Serverless deferral, HSM legacy clusters).

## Pre-flight: cluster metadata gate (run before classification)

Before evaluating any dimension, classify the cluster itself. Several
cluster attributes **short-circuit** the audit — misclassifying them
produces false positives that erode operator trust.

**Live-account pre-flight checks (skip if doing offline metadata audit):**

1. **Confirm the cluster exists and is reachable.** `aws redshift
   describe-clusters --cluster-identifier <id> --profile <p>` — fail
   closed (skip the audit, surface an ERROR) if it returns
   `ClusterNotFound`. A cluster in `deleting` or `final-snapshot` state
   cannot be remediated in place; note the lifecycle state in the
   verdict.
2. **Verify the caller can run `redshift:Describe*` AND
   `ec2:DescribeSecurityGroups`.** The SG dimension requires
   cross-service access — a read-only auditor role scoped to Redshift
   only will silently emit CONFIG_GAP false positives because it cannot
   see the SG rules. Verify BEFORE the audit, not after.
3. **Snapshot the cluster's parameter group application.** Reboot
   windows are required for parameter-group changes that affect SSL.
   Confirm whether a recent reboot is in flight
   (`ClusterParameterGroupStatus: Applying` means pending reboot).
4. **Confirm whether audit logging was ever enabled then disabled.**
   `describe-logging-status` returns `LoggingEnabled: false` for both
   "never enabled" and "previously enabled, now off". For forensics,
   check the bucket for prior log objects under the cluster's prefix.

| Attribute | Value | Effect on audit |
|---|---|---|
| `ClusterStatus` | `available`, `modifying`, `rebooting` | Proceed normally. `modifying`/`rebooting` may mean a parameter-group change is mid-apply. |
| `ClusterStatus` | `deleting`, `final-snapshot` | Cluster is being decommissioned — emit verdict with a note that remediation is N/A until the cluster is recreated. |
| `ClusterStatus` | `paused` (RA3 limit, rare) | Cluster is administratively paused. Encryption / SSL / logging dimensions still audit. |
| `NumberOfNodes: 1` | Single-node | Single-node clusters do **not** provide continuous availability during node failure. Note as an operational risk (not a verdict driver). Multi-AZ deployment (the `MultiAZ` flag on supported node types) is the availability dimension — separate from security. |
| `NodeType: serverless` or input is a Redshift Serverless workgroup | **Skip this skill.** Redshift Serverless has a different API surface (`redshift-serverless get-workgroup`, no `PubliclyAccessible`, no `ClusterParameterGroupName` — SSL is `require_ssl` on the config). Defer to a Serverless-specific audit. Emit ERROR with a routing note. |
| `HsmClientCertificateIdentifier` present | **Legacy HSM-encrypted cluster.** Pre-2017 Redshift supported on-prem HSM encryption. HSM-managed clusters report `Encrypted: true` but bypass KMS entirely. Treat as encrypted for verdict purposes; flag as a deprecation risk (HSM integration is end-of-life). |
| `ElasticIpStatus: ElasticIp` present | **EIP attached.** A public IP pinned to the cluster. Combined with `PubliclyAccessible: true`, this is a stable, DNS-portable public database endpoint — worse than an ephemeral public IP because it survives stop/start. |
| `KmsKeyId: null` AND `Encrypted: true` | **AWS-managed KMS key** (`aws/redshift`). Encryption is on; you do NOT control rotation or cross-account policy. Note in findings — CMK migration is a hardening step, not a security gap. |
| `KmsKeyId: <arn>` AND `Encrypted: true` | **Customer-managed KMS key.** Preferred posture. Cross-reference the key policy via the kms-key-policy-auditor skill. |
| `ClusterParameterGroupName: default.redshift-1.0` (or `.0` for any engine version) | **Default parameter group.** Cannot be modified — `require_ssl` and `enable_user_activity_logging` cannot be set to `true` on the default PG. Any non-default parameter value requires migrating to a custom PG. |

**If the cluster metadata is malformed** (missing `ClusterIdentifier`,
missing `PubliclyAccessible`, missing `Encrypted`), output:

```text
CLUSTER: <id-or-unknown>
VERDICT: ERROR
REASON: Cluster metadata is incomplete — cannot classify (missing <field>).
REMEDIATION: Re-fetch with `aws redshift describe-clusters --cluster-identifier <id> --output json` and re-audit.
```

## Process — Classification logic (apply in order, first match wins)

### Step 0: Expert knowledge — non-obvious Redshift behaviours that change classification

Fourteen non-obvious Redshift behaviours (PubliclyAccessible vs EnhancedVPCRouting, require_ssl scope, read-only default parameter group, AWS-managed key, encryption immutability, snapshot retention expiry and range, enable-logging vs enable_user_activity_logging, port 5439, cross-region snapshot copy, paused clusters, single-node exposure, CloudTrail control-plane only): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load before classification; Steps 1-6 below assume these constraints.

### Step 1: Public accessibility (highest priority — internet-exposed data warehouse)

If `PubliclyAccessible: true`:

- **Verdict: PUBLIC.** The cluster is assigned a public IP and accepts
  connections from `0.0.0.0/0` on the cluster port (subject to SG
  rules). Even if the SG restricts ingress to a corporate CIDR, the
  cluster responds to public TCP probes (SYN-ACK) — it is discoverable
  by any internet scanner, and any future SG widening instantly exposes
  it. A public Redshift cluster is a public petabyte-scale database.
- The presence of an Elastic IP (`ElasticIpStatus.ElasticIp` set) makes
  the exposure *stable* — the public IP survives stop/start. Note this
  in FINDINGS; it does not change the verdict but raises the
  operational risk.

PubliclyAccessible is evaluated first because it is the only dimension
where the cluster is **directly attackable from anywhere on the
internet**. Encryption, SSL, and logging are all important but
presuppose the cluster is reachable; PUBLIC short-circuits that
assumption.

### Step 2: Encryption-at-rest (immutable post-creation)

If `Encrypted: false`:

- **Verdict: NO_ENCRYPTION.** Data-at-rest is unencrypted. Snapshots
  inherit the cluster's encryption state (an unencrypted cluster
  produces unencrypted snapshots; you can copy a snapshot with
  encryption enabled, which is one path to a migration). The KMS key
  flag is irrelevant when `Encrypted: false`.

If `Encrypted: true`:
- With `KmsKeyId: null` → AWS-managed key (`aws/redshift`). OK for this
  dimension. Note as an additive finding if CMK is required by the
  compliance framework.
- With `KmsKeyId: <arn>` → customer-managed key. OK for this dimension.
  Recommend cross-referencing the key policy via the
  kms-key-policy-auditor skill (the key's policy is a separate audit
  surface).

Encryption is evaluated second because it is the second-highest blast
radius (after internet exposure): if an unencrypted snapshot leaks or
the underlying storage is improperly decommissioned, the data is
plaintext.

### Step 3: require_ssl parameter group enforcement

Inspect the parameter group attached to the cluster
(`ClusterParameterGroupName`) and its parameter list. Find the
`require_ssl` parameter.

- **`require_ssl: false` (any source)** → **Verdict: NO_SSL.** SQL
  clients MAY connect over plaintext. Compliance frameworks (PCI-DSS
  4.1, HIPAA Transport Encryption, SOC 2 CC6.1) require TLS in transit.
  Redshift's wire protocol supports SSL; `require_ssl: true` enforces
  it.

- **`require_ssl: true`** → OK for this dimension.
- **`require_ssl` parameter absent from the response** → treat as
  `false` (the engine default is false). Flag as NO_SSL.

**Default parameter group trap:** if the cluster is on
`default.redshift-1.0` and `Source: engine-default`, the operator has
not actively decided. Remediation requires migrating to a custom PG —
emphasise this in REMEDIATION. A custom PG with `require_ssl: false`
and `Source: user` is an explicit operator decision to allow plaintext
(a deliberate misconfiguration, not a default).

**Pending-reboot trap:** if `ClusterParameterGroupStatus: Applying` or
`pending-reboot`, a recent parameter change has not yet taken effect.
The current effective value is the OLD value, not the new one. Surface
the pending value in the FINDINGS; the verdict reflects the current
effective state.

### Step 4: Audit logging (S3 export)

Inspect `describe-logging-status`. The key field is `LoggingEnabled`.

- **`LoggingEnabled: false`** → **Verdict: NO_AUDIT_LOG.** Connection,
  user-activity, and DDL events are not being exported to S3. This
  eliminates forensic capability for "who ran what query when" and
  breaks compliance evidence chains (PCI-DSS 10.2, HIPAA §164.312(b),
  SOC 2 CC7.2).

- **`LoggingEnabled: true`** → OK for this dimension. Note the bucket
  name and prefix in FINDINGS; recommend verifying the bucket's
  object-lock / retention policy and access controls separately.

Audit logging is evaluated fourth because it is the forensic
prerequisite for investigating the other findings. Without it, a
PUBLIC+NO_ENCRYPTION breach cannot be reconstructed.

### Step 5: Configuration gaps (additive findings)

Evaluate the remaining dimensions and surface any failures as CONFIG_GAP
findings. If any of the following fail AND Steps 1-4 all passed, the
verdict is **CONFIG_GAP**.

| Sub-check | Failure condition | Why it matters |
|---|---|---|
| **Automated snapshots** | `AutomatedSnapshotRetentionPeriod: 0` | PITR disabled. Existing automated snapshots expire within the next snapshot window. Manual snapshots are unaffected but require active management. |
| **Enhanced VPC routing** | `EnhancedVPCRouting: false` | `COPY` / `UNLOAD` traffic bypasses VPC SGs, NACLs, and VPC endpoints — data path is not subject to network controls. Engine default is `false`. |
| **VPC security group ingress on cluster port** | Any SG rule with `0.0.0.0/0` (or `::/0`) on the cluster's TCP port (default 5439, configurable via `Endpoint.Port`) | Even with `PubliclyAccessible: false`, an `0.0.0.0/0` SG rule on the cluster port is a CONFIG_GAP — a future flip of `PubliclyAccessible` to `true` instantly exposes the cluster. Note: SG ingress does NOT make a private cluster public; it expands the in-VPC attack surface. |
| **User-activity logging** | `enable_user_activity_logging: false` parameter value | STL_QUERY retains query text for ~3-7 days; without user_activity_logging exported to S3 (via the audit log pipeline), long-horizon forensic queries are impossible. Treat as CONFIG_GAP (additive to Step 4 — if Step 4 failed, this is folded into NO_AUDIT_LOG). |
| **Snapshot retention below compliance floor** | `AutomatedSnapshotRetentionPeriod: 1` on a production cluster | The engine default is 1 day. PCI/HIPAA typically require 7+; flag as a soft CONFIG_GAP if compliance framework applies. |
| **Cross-region snapshot copy absent** | `ClusterSnapshotCopyStatus` is absent on a production cluster | Single-region snapshots = no DR. Flag as a resilience CONFIG_GAP (not security). |

For the SG check specifically: the SG dimension surfaces the *exposure*
of the cluster within its VPC. SG rules from corporate CIDRs
(`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) are typically fine;
`0.0.0.0/0` on the cluster port is the canonical misconfiguration.

### Step 6: Aggregation — OK verdict

If all dimensions pass (PUBLIC not set, Encrypted true, require_ssl true,
LoggingEnabled true, no CONFIG_GAP sub-findings), the verdict is **OK**.

```text
verdict_priority = PUBLIC > NO_ENCRYPTION > NO_SSL > NO_AUDIT_LOG > CONFIG_GAP > OK
```

Apply in order; the first matching step wins. ALL findings (including
non-verdict-driving ones) appear in the FINDINGS list.

## Output format (per cluster)

```text
CLUSTER: <cluster-identifier>
VERDICT: PUBLIC | NO_ENCRYPTION | NO_SSL | NO_AUDIT_LOG | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [PUBLIC] <finding description (Step 1)>
  - [NO_SSL] <finding description (Step 3)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — public cluster with encryption disabled

```text
CLUSTER: public-cluster-no-encryption
VERDICT: PUBLIC
REASON: PubliclyAccessible is true, placing the cluster on the public
internet on TCP 5439 (Step 1). Encryption is also disabled, require_ssl
is false, and S3 audit logging is off — every dimension fails.
FINDINGS:
  - [PUBLIC] PubliclyAccessible: true — cluster accepts connections from
    0.0.0.0/0 on the cluster port (Step 1)
  - [NO_ENCRYPTION] Encrypted: false — data-at-rest is plaintext (Step 2)
  - [NO_SSL] require_ssl: false in default.redshift-1.0 — clients may
    connect over plaintext (Step 3)
  - [NO_AUDIT_LOG] LoggingEnabled: false — no S3 audit trail (Step 4)
  - [CONFIG_GAP] EnhancedVPCRouting: false — COPY/UNLOAD bypasses VPC
    controls (Step 5)
  - [CONFIG_GAP] SG sg-0aaa11112222 has 0.0.0.0/0 on TCP 5439 (Step 5)
REMEDIATION:
  1. PUBLIC — Set PubliclyAccessible to false: see CLI below. This
     requires a client reboot. If public access is INTENTIONAL (e.g., a
     partner-data workload), restrict the SG to specific partner CIDRs
     immediately.
  2. NO_ENCRYPTION — Plan an encryption migration: provision a new
     encrypted cluster, UNLOAD to S3, COPY into the new cluster, redirect
     downstream tools, decommission the old cluster. Encryption cannot be
     toggled on an existing cluster.
  3. NO_SSL — Create a custom parameter group with require_ssl: true,
     associate it with the cluster, and reboot for the change to take
     effect.
  4. NO_AUDIT_LOG — Enable S3 audit logging:
     aws redshift enable-logging --cluster-identifier public-cluster-no-encryption \
       --log-destination-name S3 --bucket-name audit-logs-111111111111 \
       --s3-key-prefix redshift/public-cluster-no-encryption/
  5. CONFIG_GAP — Enable EnhancedVPCRouting (requires cluster reboot) and
     restrict the SG ingress to known CIDRs on the cluster port.
```

## Edge-case handling

Nine edge cases (modifying/rebooting states, default parameter group, Multi-AZ, RA3/DC2/DS2 node types, HSM legacy, snapshot copy status, Serverless deferral, AWS-managed key, non-default port): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Consult after the ordered steps when the cluster metadata is unusual.

## Anti-Patterns — NEVER

- NEVER classify `PubliclyAccessible: true` as anything other than
  PUBLIC. The flag is a direct internet endpoint on TCP 5439/5440. SG
  rules may restrict ingress, but the cluster is still discoverable and
  attackable by any internet scanner. A public data warehouse is the
  highest-impact Redshift misconfiguration.

- NEVER recommend "just enable encryption" on an existing cluster.
  Redshift encryption is immutable per cluster. The only remediation
  is a new cluster + UNLOAD/COPY migration. Stating otherwise causes
  operators to attempt `modify-cluster --encrypted` (which does not
  exist) and lose trust in the audit.

- NEVER treat `require_ssl: false` from the default parameter group as
  an operator decision. `Source: engine-default` means the operator
  has not hardened this — they may not even know the parameter exists.
  Remediation requires migrating to a custom PG (the default PG is
  read-only).

- NEVER assume `enable-logging` and `enable_user_activity_logging` are
  the same thing. `enable-logging` (the API) exports audit events to
  S3. `enable_user_activity_logging` (the parameter) logs every SQL
  query to STL_QUERY. They are separate controls with separate
  forensic value. Treat absence of either as a gap.

- NEVER assume CloudTrail covers Redshift SQL activity. CloudTrail logs
  control-plane events (CreateCluster, ModifyCluster, DeleteCluster).
  It does NOT log data-plane SQL queries — that is exclusively the
  domain of `enable-logging` S3 audit logs. "We have CloudTrail" does
  not satisfy "we audit database activity" for Redshift.

- NEVER conflate `PubliclyAccessible: false` with "no internet exposure
  for data transfers". `EnhancedVPCRouting: false` (the default) means
  COPY/UNLOAD traffic to S3 traverses the public AWS network path,
  bypassing your VPC's SGs, NACLs, and VPC endpoints. Privacy of the
  cluster endpoint and privacy of the bulk-transfer data path are
  independent concerns.

- NEVER treat a single-node cluster as having high availability.
  Single-node clusters have no replication and no failover. Destructive
  queries (DROP TABLE, TRUNCATE) affect the entire dataset with no
  redundant copy. Note this as an operational risk; do not let it
  drive the security verdict.

- NEVER flag `KmsKeyId: null` with `Encrypted: true` as an encryption
  gap. This is the AWS-managed key (`aws/redshift`) — encryption is
  on. Rotates annually on AWS's schedule. Acceptable for most
  compliance frameworks. Flag CMK as a hardening opportunity, not a
  finding.

- NEVER attempt to apply this skill to a Redshift Serverless workgroup.
  Serverless has a different API surface (no `PubliclyAccessible`, no
  `ClusterParameterGroupName`, SSL enforced via `config-parameters` on
  the workgroup). Emit ERROR with a routing note — misclassifying a
  Serverless workgroup as PUBLIC or NO_SSL is a false positive.

- NEVER assume `AutomatedSnapshotRetentionPeriod: 0` only disables
  future snapshots. Redshift immediately begins expiring existing
  automated snapshots. Operators setting retention to 0 to "save cost"
  without first converting critical snapshots to manual lose PITR
  irreversibly within hours.

- NEVER recommend modifying a default parameter group. The default PG
  (`default.redshift-1.0`) is read-only — `modify-cluster-parameter-group`
  fails. Remediation requires creating a custom PG and associating it
  with the cluster.

- NEVER treat an SG with `0.0.0.0/0` on TCP 5439 as making the cluster
  public. The cluster is public ONLY if `PubliclyAccessible: true`. SG
  `0.0.0.0/0` ingress on a private cluster is a CONFIG_GAP — it
  expands the in-VPC attack surface and sets up a future exposure if
  the flag is flipped, but it does not by itself expose the cluster to
  the internet.

- NEVER evaluate the SG ingress on the wrong port. The cluster port is
  in `Endpoint.Port` (default 5439, customisable up to 65535). SG
  rules matching TCP 5432 (Postgres default) silently fail to permit
  traffic. Read the actual port from the metadata, not the default.

- NEVER flag a cluster in `paused` state as safer or out-of-scope.
  Paused clusters retain their encryption, SG, and logging posture;
  the audit is identical. Pause is a cost-optimisation, not a security
  control.

## Pre-flight safety checks (run before any remediation CLI)

Seven pre-flight safety checks (CONFIRM gate, reboot warnings, encryption migration scope, pre-change snapshot, audit bucket ownership, cross-region cost, shared-SG verification): moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Defense-in-depth before any remediation CLI.

## Remediation guidance

**Remediation ordering principle:** additive changes first (enable
logging, associate a new PG), destructive / state-changing changes last
(modify cluster, reboot). Public accessibility and encryption are the
two findings that cannot be silently fixed in place — plan migrations,
not toggles.

Per-verdict remediation playbooks with full CLI blocks (PUBLIC, NO_ENCRYPTION UNLOAD/COPY migration, NO_SSL custom parameter group, NO_AUDIT_LOG enable-logging, CONFIG_GAP sub-findings, OK follow-ups): moved verbatim to [references/remediation-procedures.md](references/remediation-procedures.md).
Emit per-finding remediation from that reference.

## Recent AWS features (2024-2026)

Four recent AWS features 2024-2026 (Serverless enhancements, Aurora Zero-ETL, data sharing, Redshift ML): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Consult before citing feature limits or recency.

## Related skills

- **kms-key-policy-auditor:** audit the KMS key policy when a
  customer-managed key encrypts the cluster. The cluster audit treats
  the key as a black box; the key-policy audit determines who can
  decrypt cluster snapshots.
- **ec2-security-group-auditor:** deeper SG analysis including
  prefix-list composition and cross-VPC exposure (the cluster audit
  checks only the cluster port's exposure on the attached SGs).
- **s3-public-access-auditor:** audit the S3 bucket receiving UNLOAD
  exports or audit logs — a private cluster with a public UNLOAD bucket
  silently exfiltrates data.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 non-obvious behaviours, edge-case handling, recent AWS features (2024-2026).
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — Pre-flight safety checks before any remediation CLI.
- [references/remediation-procedures.md](references/remediation-procedures.md) — Per-verdict remediation playbooks with CLI blocks.

## Domain

AWS CloudOps / Redshift Analytics Security & Compliance.

## AWS documentation

- **Amazon Redshift documentation** — https://docs.aws.amazon.com/redshift/latest/dg/welcome.html
- **Security in Amazon Redshift** — https://docs.aws.amazon.com/redshift/latest/dg/security.html
- **Amazon Redshift API Reference** — https://docs.aws.amazon.com/redshift/latest/APIReference/
- **AWS CLI Redshift reference** — https://docs.aws.amazon.com/cli/latest/reference/redshift/
- **Amazon Redshift Management Guide** — https://docs.aws.amazon.com/redshift/latest/mgmt/welcome.html
- **Redshift Serverless** — https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-whatis.html
