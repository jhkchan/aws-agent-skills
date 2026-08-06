---
name: redshift-cluster-auditor
description: >-
  Audits Amazon Redshift provisioned clusters for security posture and
  configuration gaps — public accessibility (internet-exposed cluster),
  KMS encryption-at-rest (immutable post-creation), require_ssl parameter
  group enforcement, S3 audit logging, VPC security-group ingress on the
  cluster port, automated-snapshot retention (PITR), and enhanced VPC
  routing (COPY/UNLOAD traffic path). Emits a deterministic categorical
  verdict (PUBLIC | NO_ENCRYPTION | NO_SSL | NO_AUDIT_LOG | CONFIG_GAP | OK)
  per cluster with enumerated findings and specific remediation. Use when
  reviewing a Redshift cluster before production deployment, auditing
  encryption or SSL posture, checking S3 audit logging coverage, validating
  snapshot retention, or hardening data-warehouse security.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline metadata classification.
  Live-account audits use aws redshift describe-clusters, describe-logging-status,
  describe-cluster-parameter-groups (with describe-cluster-parameters for the
  PG), aws ec2 describe-security-groups, and aws kms describe-key (AWS CLI v2,
  SSO or key-based credentials).
keywords:
  - Redshift
  - data warehouse
  - PubliclyAccessible
  - encryption
  - KMS
  - require_ssl
  - SSL
  - TLS
  - parameter group
  - audit logging
  - S3 audit log
  - enable_user_activity_logging
  - automated snapshots
  - AutomatedSnapshotRetentionPeriod
  - enhanced VPC routing
  - EnhancedVPCRouting
  - COPY
  - UNLOAD
  - VPC security group
  - cluster port 5439
  - data-warehouse hardening
  - compliance
  - Redshift Serverless
tags: [redshift, analytics, security, encryption, ssl, audit-logging, snapshots, vpc, compliance, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  verdict_shape: "PUBLIC | NO_ENCRYPTION | NO_SSL | NO_AUDIT_LOG | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a Redshift provisioned cluster before production deployment,
    auditing encryption-at-rest, validating require_ssl enforcement, checking
    S3 audit logging coverage, inspecting automated-snapshot retention,
    evaluating enhanced VPC routing posture, or hardening a data warehouse
    for a compliance review.
  activation_triggers:
    - "audit this Redshift cluster"
    - "is my Redshift cluster public"
    - "is encryption enabled on Redshift"
    - "is require_ssl on"
    - "is Redshift audit logging configured"
    - "are automated snapshots enabled"
    - "enhanced VPC routing Redshift"
    - "Redshift security group audit"
    - "harden this data warehouse"
  invocation_schema: >-
    Input: either (a) a describe-clusters Cluster block, optionally paired
    with describe-logging-status, describe-cluster-parameters (for the
    attached parameter group), and describe-security-groups outputs, OR
    (b) a ClusterIdentifier for live-account audit.
    Output: deterministic CLUSTER/VERDICT/REASON/FINDINGS/REMEDIATION block
    per cluster, where VERDICT ∈ {PUBLIC, NO_ENCRYPTION, NO_SSL,
    NO_AUDIT_LOG, CONFIG_GAP, OK, ERROR}.
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

These behaviours are easy to misjudge without operational Redshift experience.
Each changes a verdict if ignored:

- **`PubliclyAccessible: false` does NOT mean "no internet exposure" if a
  NAT Gateway + routing path exists.** Redshift with
  `PubliclyAccessible: false` is unreachable from the public internet
  (no public IP assigned). However, `COPY` from / `UNLOAD` to public S3
  endpoints still traverses the internet unless `EnhancedVPCRouting:
  true` is set. The two flags are independent — privacy of the *cluster
  endpoint* and privacy of the *data-path for bulk transfers* are
  separate concerns.

- **`require_ssl` parameter applies to client connections, not intra-
  cluster traffic.** Setting `require_ssl: true` forces SQL clients to
  connect over TLS. It does NOT encrypt the wire between compute nodes
  (which is always TLS-protected internally on RA3 / Serverless) and
  does NOT encrypt `COPY`/`UNLOAD` traffic (which is HTTPS to S3
  regardless). The compliance question "is TLS enforced?" is answered
  by this parameter for client connections.

- **The default parameter group is read-only.** `default.redshift-1.0`
  cannot be modified. A cluster using the default PG with
  `require_ssl: false` and `Source: engine-default` is reporting the
  Redshift engine default — the operator may not have actively decided.
  Remediation requires creating a custom PG, setting `require_ssl: true`,
  associating it with the cluster, AND rebooting. Treat the
  `Source: engine-default` signal as "operator has not hardened this"
  rather than "operator chose plaintext".

- **`Encrypted: true` + `KmsKeyId: null` uses the AWS-managed key
  `aws/redshift`.** The AWS-managed key rotates annually on AWS's
  schedule, has a policy controlled by AWS, and cannot be cross-account
  shared. Compliance frameworks (PCI-DSS, HIPAA, SOC 2) generally accept
  AWS-managed keys, but high-assurance audits require customer-managed
  keys for rotation control. Note the distinction in FINDINGS; do NOT
  flag the AWS-managed key as a security gap.

- **Encryption is immutable per cluster.** Unlike RDS (snapshot + copy
  toggles encryption) or EBS (online modify), Redshift encryption is
  fixed at cluster creation. To "enable" encryption on an unencrypted
  cluster you must: (1) provision a new encrypted cluster, (2) `UNLOAD`
  data to S3 (prefer Parquet with columnar compression), (3) `COPY`
  into the new cluster, (4) redirect downstream BI / ETL tools, (5)
  decommission the old cluster once queries validated. This is a
  multi-day migration, not a CLI toggle. State this explicitly in
  remediation — operators asking "can I just flip encryption on?" must
  be corrected.

- **`AutomatedSnapshotRetentionPeriod: 0` deletes existing automated
  snapshots within hours.** Setting retention to zero does NOT just stop
  future snapshots — Redshift begins expiring existing automated
  snapshots immediately (typically within the next snapshot window,
  ~1 hour). Manual snapshots are NOT affected. If an operator sets
  retention to 0 to "save cost" without first converting critical
  automated snapshots to manual, they lose PITR irreversibly.

- **`AutomatedSnapshotRetentionPeriod` range is 0 to 35.** Values above
  35 are rejected by the API. The default is 1 day (effectively
  overnight-only recovery). Compliance postures typically require 7+;
  35 is the maximum. Manual snapshots have no retention cap and persist
  until explicitly deleted.

- **`enable_user_activity_logging` is a parameter-group setting distinct
  from `aws redshift enable-logging`.** The `enable-logging` API
  exports audit events (connections, DDL, DML authorisation checks) to
  S3 in near-real-time. The `enable_user_activity_logging` parameter
  logs every SQL statement to the STL_QUERY system table at high
  volume. Both are needed for full forensic coverage: enable-logging
  gives you a tamper-evident S3 trail; user_activity_logging gives you
  the full query text. Treat `enable-logging` off as NO_AUDIT_LOG; treat
  `enable_user_activity_logging` off as an additive CONFIG_GAP finding.

- **`EnhancedVPCRouting: false` is the engine default.** With it off,
  `COPY` and `UNLOAD` traffic leaves the cluster over the public AWS
  network path to S3 (HTTPS, still encrypted, but not subject to your
  VPC's security groups, network ACLs, or VPC endpoints). With it on,
  that traffic flows through your VPC, enabling S3 Gateway VPC endpoint
  enforcement. Many compliance frameworks require EnhancedVPCRouting on
  because it closes the "data-path bypasses network controls" gap.

- **The Redshift cluster port defaults to 5439, not 5432.** A common
  misconfiguration copies RDS-style SG rules permitting TCP 5432 from
  app CIDRs, which silently fail to permit any traffic. Conversely,
  `0.0.0.0/0` on TCP 5439 is the canonical "cluster open to the world"
  SG rule. The port is configurable at cluster creation
  (`ClusterPort`, range 1150-65535); JK SecureListen deployments use
  5440. Always read the actual port from `Endpoint.Port`, not assume.

- **Snapshot copy grants cross-region DR but is configured separately.**
  `ClusterSnapshotCopyStatus` (present on the cluster) reports whether
  automated snapshots are copied to a DR region. Absent
  `DestinationRegion` is a DR gap (not a security verdict driver, but
  noted in FINDINGS as resilience).

- **A paused cluster still incurs storage charges and still has its
  encryption + SG posture.** Pause is a cost-optimisation action, not a
  security control. Do not treat paused clusters as safer; their
  configuration dimensions audit identically to available clusters.

- **`PubliclyAccessible: true` on a single-node cluster is the worst-
  case Redshift exposure.** Single-node clusters have no replication
  and no HA — an attacker with the credentials (or a CVE) has access to
  the entire dataset with no redundancy to recover from destructive
  queries. Treat as PUBLIC with an additional operational risk note.

- **CloudTrail logs Redshift *control-plane* events (CreateCluster,
  ModifyCluster, DeleteCluster) by default.** It does NOT log data-
  plane SQL queries — that is what `enable-logging` (S3 audit logs) is
  for. "We have CloudTrail, so we have audit coverage" is a false
  belief for Redshift data-plane activity.

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

- **Cluster in `modifying` / `rebooting` state.** Audit normally. Note
  in FINDINGS that parameter-group changes may be pending; the verdict
  reflects the *current effective* state, not the pending one.

- **Cluster using `default.redshift-1.0` parameter group.** Default PGs
  are read-only — `require_ssl` and `enable_user_activity_logging`
  cannot be modified in place. Remediation requires creating a custom
  PG, associating, and rebooting. Surface this explicitly so operators
  do not attempt `modify-cluster-parameter-group` on the default PG
  (which fails).

- **Multi-AZ deployment.** `MultiAZ: true` (on supported node types) is
  an availability dimension, not a security dimension. Note its presence
  or absence as an operational finding; do not let it drive the verdict.

- **RA3 vs DC2 / DS2 node types.** DS2 (dense storage) is end-of-life
  and being forcibly retired. DC2 (dense compute) is current for
  compute-bound workloads. RA3 (managed storage) is the recommended
  current generation with separated compute + storage. Flag DS2 in
  FINDINGS as a deprecation risk (operational, not a verdict driver).

- **HSM-encrypted legacy cluster.** `HsmClientCertificateIdentifier` set
  + `Encrypted: true` indicates pre-2017 HSM-managed encryption. Treat
  as Encrypted OK for Step 2; flag in FINDINGS that HSM integration is
  deprecated and the cluster should be migrated to KMS-managed
  encryption.

- **ClusterSnapshotCopyStatus present.** Cross-region snapshot copy is
  configured. Note in FINDINGS as a positive resilience signal. Absent
  on a production cluster is a CONFIG_GAP (resilience, not security).

- **Redshift Serverless input.** Serverless workgroups do not have
  `PubliclyAccessible` or `ClusterParameterGroupName`. They have a
  `config-parameters` list including `require_ssl` and the base network
  is always VPC-only. Do NOT attempt to apply this skill to Serverless —
  emit ERROR with a routing note.

- **Cluster with `KmsKeyId: null` AND `Encrypted: true`.** AWS-managed
  key in use. Treat as Encrypted OK; note the AWS-managed vs
  customer-managed distinction in FINDINGS. Recommend CMK for
  high-assurance compliance postures.

- **`Endpoint.Port` is non-default.** Always read the cluster port from
  `Endpoint.Port` (range 1150-65535). SG rules matching TCP 5439 are
  the canonical check, but if the cluster uses 5440 (JK SecureListen)
  or any custom port, evaluate SG ingress on the actual port.

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

- **MANDATORY CONFIRMATION GATE.** Before any destructive or
  state-changing operation (`modify-cluster`, `reboot-cluster`,
  `enable-logging`, `disable-logging`, `delete-cluster`,
  `modify-cluster-snapshot-schedule`), the auditor MUST emit:
  `CONFIRM: About to <action> on cluster <id> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. This
  gate prevents automated pipelines from silently modifying data
  warehouses.
- **Reboot warnings.** `modify-cluster` changes to
  `ClusterParameterGroupName`, `EnhancedVPCRouting`, `PubliclyAccessible`,
  or `Encrypted` (not supported — see Step 2) require a cluster reboot.
  Reboots terminate in-flight queries, fail over leader-node connections,
  and may take 10-30 minutes on large clusters. Surface this BEFORE the
  operator approves.
- **Encryption migration is irreversible and multi-day.** A NO_ENCRYPTION
  remediation involves provisioning a new cluster, UNLOAD/COPY migration,
  application cutover, and decommissioning. Do NOT represent this as a
  one-step CLI command. Provide the full migration workflow and warn
  that downstream BI tools must be repointed.
- **Snapshot before parameter-group or routing changes.** Capture the
  current state with a manual snapshot before modifying the parameter
  group or enhanced VPC routing:
  `aws redshift create-snapshot-cluster-schedule` or
  `aws redshift create-cluster-snapshot --cluster-identifier <id>
  --snapshot-identifier pre-audit-<id>-$(date +%s)`.
  This is the rollback path if the new PG breaks query patterns.
- **Confirm audit-log bucket ownership.** Before
  `aws redshift enable-logging`, verify the S3 bucket exists, is in the
  expected account, has object-lock or appropriate retention, and the
  Redshift service principal can write to it. Misconfigured buckets
  silently fail logging with no error surfaced in `describe-logging-status`
  beyond `LoggingEnabled: false` and `LogFileLastWritten` stalling.
- **Cross-region snapshot copy has cost implications.** Enabling
  `modify-snapshot-copy-destination` incurs cross-region data transfer
  + snapshot storage in the DR region. Surface the cost estimate before
  recommending.
- **Pre-flight for SG changes.** Before
  `aws ec2 revoke-security-group-ingress`, verify no other cluster or
  service shares the SG. Shared SGs are common in legacy Redshift
  deployments — revoking a rule may break adjacent workloads. Use
  `aws ec2 describe-network-interfaces --groups <sg-id>` to check
  associations first.

## Remediation guidance

**Remediation ordering principle:** additive changes first (enable
logging, associate a new PG), destructive / state-changing changes last
(modify cluster, reboot). Public accessibility and encryption are the
two findings that cannot be silently fixed in place — plan migrations,
not toggles.

### For PUBLIC — public accessibility (Step 1)

1. **If public access is NOT intentional:** set
   `PubliclyAccessible: false` and reboot. CLI:
   ```bash
   aws redshift modify-cluster --cluster-identifier <id> \
     --no-publicly-accessible --profile <p>
   aws redshift reboot-cluster --cluster-identifier <id> --profile <p>
   ```
   This requires a maintenance window; queries in flight are terminated.
2. **If public access IS intentional** (rare — partner-data workload
   with no VPC peering): restrict the SG to the specific partner
   CIDRs. Do NOT leave `0.0.0.0/0` on the cluster port. Require SSL.
3. **Verify** with `aws redshift describe-clusters --cluster-identifier
   <id>` that `PubliclyAccessible: false` is effective.
4. **Assume breach.** Audit CloudTrail for `ModifyCluster` calls
   during the exposure window. Check S3 audit logs (if enabled) for
   unexpected source IPs in STL_CONNECTION_LOG.

### For NO_ENCRYPTION — encryption-at-rest (Step 2)

There is NO in-place remediation. The migration workflow:

1. Provision a new encrypted cluster (preferably RA3 with a CMK):
   ```bash
   aws redshift create-cluster --cluster-identifier <id>-encrypted \
     --node-type ra3.xlplus --number-of-nodes <n> \
     --master-username <u> --master-user-password <pwd> \
     --encrypted --kms-key-id <cmk-arn> \
     --cluster-subnet-group-name <sg> --vpc-security-group-ids <sg-id> \
     --cluster-parameter-group-name <custom-pg-with-require-ssl> \
     --publicly-accessible false --enhanced-vpc-routing --profile <p>
   ```
2. `UNLOAD` from the old cluster to S3 (Parquet recommended):
   ```sql
   UNLOAD ('SELECT * FROM schema.table')
   TO 's3://migration-bucket/<id>/'
   IAM_ROLE '<role-arn>' FORMAT PARQUET ENCRYPTED;
   ```
3. `COPY` into the new cluster:
   ```sql
   COPY schema.table FROM 's3://migration-bucket/<id>/'
   IAM_ROLE '<role-arn>' FORMAT PARQUET;
   ```
4. Validate row counts, validate downstream BI dashboards, redirect
   DNS / connection strings.
5. Decommission the old cluster only after validation:
   ```bash
   aws redshift delete-cluster --cluster-identifier <id> \
     --final-cluster-snapshot-identifier final-<id>-$(date +%s)
   ```
   Always take a final manual snapshot before deletion.

### For NO_SSL — require_ssl enforcement (Step 3)

1. Create a custom parameter group:
   ```bash
   aws redshift create-cluster-parameter-group \
     --parameter-group-name require-ssl-pg \
     --parameter-group-family redshift-1.0 \
     --description "Custom PG with require_ssl" --profile <p>
   aws redshift modify-cluster-parameter-group \
     --parameter-group-name require-ssl-pg \
     --parameters ParameterName=require_ssl,ParameterValue=true \
     --profile <p>
   ```
2. Associate with the cluster (requires reboot):
   ```bash
   aws redshift modify-cluster --cluster-identifier <id> \
     --cluster-parameter-group-name require-ssl-pg --profile <p>
   aws redshift reboot-cluster --cluster-identifier <id> --profile <p>
   ```
3. Verify: `aws redshift describe-cluster-parameters
   --parameter-group-name require-ssl-pg` shows `require_ssl: true`.

### For NO_AUDIT_LOG — S3 audit logging (Step 4)

1. Enable logging:
   ```bash
   aws redshift enable-logging --cluster-identifier <id> \
     --log-destination-name S3 --bucket-name <audit-bucket> \
     --s3-key-prefix redshift/<id>/ --profile <p>
   ```
2. Verify: `aws redshift describe-logging-status --cluster-identifier
   <id>` shows `LoggingEnabled: true`.
3. Verify bucket ownership and retention policy separately — S3 audit
   logs are only useful if the bucket is tamper-evident (object-lock
   recommended).
4. For full forensic coverage, also set
   `enable_user_activity_logging: true` in the parameter group.

### For CONFIG_GAP — sub-finding remediation

**Automated snapshots disabled (retention 0):**
```bash
aws redshift modify-cluster --cluster-identifier <id> \
  --automated-snapshot-retention-period 7 --profile <p>
```
Re-enable within the snapshot window to recover PITR. Compliance
postures typically require 7-35 days.

**Enhanced VPC routing off:**
```bash
aws redshift modify-cluster --cluster-identifier <id> \
  --enhanced-vpc-routing --profile <p>
aws redshift reboot-cluster --cluster-identifier <id> --profile <p>
```
After enabling, COPY/UNLOAD traffic flows through your VPC — verify S3
Gateway VPC endpoint exists or COPY/UNLOAD may fail.

**SG with 0.0.0.0/0 on cluster port:**
```bash
aws ec2 revoke-security-group-ingress --group-id <sg-id> \
  --ip-permissions IpProtocol=tcp,FromPort=<cluster-port>,ToPort=<cluster-port>,IpRanges=[{CidrIp=0.0.0.0/0}] \
  --profile <p>
aws ec2 authorize-security-group-ingress --group-id <sg-id> \
  --ip-permissions IpProtocol=tcp,FromPort=<cluster-port>,ToPort=<cluster-port>,IpRanges=[{CidrIp=10.0.0.0/16}] \
  --profile <p>
```
Verify no other resource shares this SG before revoking.

**User-activity logging off:** set `enable_user_activity_logging: true`
in the custom parameter group (same workflow as require_ssl).

### For OK

1. No remediation required.
2. Recommend periodic re-audit (configuration drift is common on
   long-running clusters).
3. Recommend cross-referencing the KMS key policy via the
   kms-key-policy-auditor skill when a CMK is in use.
4. Recommend verifying the audit-log S3 bucket's object-lock / retention
   policy separately.
5. For multi-AZ clusters, verify the `MultiAZ` deployment status is
   still in sync across AZs.

## Recent AWS features (2024-2026)

- **Redshift Serverless GA and enhanced (2024-2025):** Redshift Serverless auto-scales compute based on workload. Auditors should note that Serverless workgroups have a different audit surface than provisioned clusters — verify encryption, VPC security groups, and `maxRPU` (base capacity) settings at the workgroup level.
- **Zero-ETL integration with Aurora (2024-2025):** Redshift now supports Zero-ETL integration that replicates Aurora data to Redshift automatically. Auditors should verify that the Zero-ETL integration IAM role is scoped appropriately and that data replication does not bypass encryption requirements.
- **Data sharing enhancements (2024):** Improved cross-namespace and cross-account data sharing. Auditors should verify that data share consumers have appropriate Lake Formation or Redshift-scoped permissions and that consumer namespaces are documented.
- **Redshift ML improvements (2024):** Enhanced SageMaker integration for ML model creation from Redshift. Auditors should verify that the Redshift-SageMaker IAM role does not have wildcard permissions.

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

## Domain

AWS CloudOps / Redshift Analytics Security & Compliance.

## AWS documentation

- **Amazon Redshift documentation** — https://docs.aws.amazon.com/redshift/latest/dg/welcome.html
- **Security in Amazon Redshift** — https://docs.aws.amazon.com/redshift/latest/dg/security.html
- **Amazon Redshift API Reference** — https://docs.aws.amazon.com/redshift/latest/APIReference/
- **AWS CLI Redshift reference** — https://docs.aws.amazon.com/cli/latest/reference/redshift/
- **Amazon Redshift Management Guide** — https://docs.aws.amazon.com/redshift/latest/mgmt/welcome.html
- **Redshift Serverless** — https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-whatis.html
