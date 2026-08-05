---
name: opensearch-domain-auditor
description: >-
  Audits Amazon OpenSearch Service (provisioned, not Serverless) domains for
  encryption-at-rest (KMS), node-to-node encryption, fine-grained access
  control (FGAC), public access via resource-policy Principal "*", dedicated
  master node sizing, and slow-log publishing to CloudWatch Logs. Emits a
  deterministic verdict (NO_ENCRYPTION | PUBLIC_ACCESS | NO_FGAC | CONFIG_GAP |
  OK) per domain with enumerated findings and CLI remediation. Use when
  reviewing an OpenSearch domain before production deployment, validating
  encryption/compliance posture, checking for public data-plane exposure, or
  hardening a cluster that grew out of a dev sandbox.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config classification. Live-account
  audits use aws opensearch describe-domain, describe-domain-config,
  list-domain-names, and describe-domain-access-policy (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - OpenSearch
  - Elasticsearch
  - AES
  - Amazon OpenSearch Service
  - encryption at rest
  - KMS
  - node-to-node encryption
  - fine-grained access control
  - FGAC
  - Advanced Security
  - public access
  - Principal star
  - es:ESHttp*
  - dedicated master
  - master node type
  - t3.small.search
  - slow logs
  - SEARCH_SLOW_LOGS
  - INDEX_SLOW_LOGS
  - LogPublishingOptions
  - VPC domain
  - cluster config
  - OpenSearch compliance
  - OpenSearch hardening
tags: [opensearch, analytics, encryption, security, fgac, master-node, slow-logs, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  verdict_shape: "NO_ENCRYPTION | PUBLIC_ACCESS | NO_FGAC | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an OpenSearch domain before production deployment, validating
    encryption compliance, checking for public data-plane exposure via resource
    policy, auditing fine-grained access control coverage, sizing dedicated
    master nodes, or wiring slow-log publishing to CloudWatch Logs.
  activation_triggers:
    - "audit this OpenSearch domain"
    - "is my OpenSearch domain public"
    - "check OpenSearch encryption at rest"
    - "OpenSearch node-to-node encryption off"
    - "OpenSearch FGAC disabled"
    - "is Advanced Security enabled"
    - "OpenSearch Principal star"
    - "dedicated master node too small"
    - "OpenSearch slow logs not published"
    - "harden OpenSearch domain"
  invocation_schema: >-
    Input: either (a) an OpenSearch domain configuration (describe-domain +
    describe-domain-config + describe-domain-access-policy +
    list-domain-names), OR (b) a domain name/ARN for live-account audit.
    Output: deterministic DOMAIN/VERDICT/REASON/FINDINGS/REMEDIATION block per
    domain, where VERDICT ∈ {NO_ENCRYPTION, PUBLIC_ACCESS, NO_FGAC, CONFIG_GAP,
    OK, ERROR}.
---

# OpenSearch Domain Auditor

## CRITICAL RULE — confirmation gate (read first)

**Every state-changing remediation** (`update-domain-config`,
`update-domain-access-policy`, `delete-domain`, `create-domain`) is **blocked**
until the operator explicitly confirms. Emit this exact prompt and halt until a
`yes` is received:

```text
CONFIRM: About to <action> on domain <name>. This affects <consequence>. Proceed? (yes/no)
```

This gate is **non-negotiable**. OpenSearch mutations can take 30 minutes to
several hours on large clusters, can trigger blue/green deployments that double
node count (cost spike), and some changes (encryption-at-rest, VPC-vs-public)
are **immutable** and require full domain recreation. Do not batch-confirm.

## Mindset

**One-line takeaway:** the verdict is the **worst** finding across all
dimensions, ordered `NO_ENCRYPTION > PUBLIC_ACCESS > NO_FGAC > CONFIG_GAP > OK`.
The most counter-intuitive facts: encryption-at-rest is **immutable** (no
toggle, requires domain recreation), `Principal: "*"` with `es:ESHttp*` is the
data-plane blast-radius multiplier (anyone with AWS credentials can read/write
every index), and FGAC cannot be enabled without node-to-node encryption
(which in turn requires HTTPS) — so a "FGAC off" finding often hides a deeper
"NTN off" root cause that must be fixed first.

OpenSearch is unusual among AWS data services in that the resource-based policy
(access policy) gates **both** the configuration API (`es:DescribeDomain`) and
the data plane (`es:ESHttp*`). A policy that is safe for S3 or KMS patterns
(`Principal: "*"` with `aws:SourceIp`) is **not** safe for OpenSearch —
`aws:SourceIp` is bypassable via VPN/NAT, and `es:ESHttp*` is full REST API
access (read every document, delete every index, change every mapping).

## Quick reference — severity thresholds

| Condition | Verdict | Rule |
|---|---|---|
| `EncryptionAtRestOptions.Enabled: false` (or absent) | **NO_ENCRYPTION** | Step 1a |
| `Principal: "*"` + `es:ESHttp*`/`es:*` + no STRONG condition | **PUBLIC_ACCESS** | Step 2a |
| `Principal: "*"` + `es:ESHttp*`/`es:*` + STRONG condition (real IP CIDR or aws:SourceAccount) | **NO_FGAC** if FGAC off else **CONFIG_GAP** | Step 2b |
| `AdvancedSecurityOptions.Enabled: false` on internet-facing domain | **NO_FGAC** | Step 3a |
| `AdvancedSecurityOptions.Enabled: false` on VPC domain | **CONFIG_GAP** | Step 3b |
| `NodeToNodeEncryptionOptions.Enabled: false` (at-rest on) | **CONFIG_GAP** | Step 4a |
| Dedicated master `t2/t3.small.search` or single dedicated master | **CONFIG_GAP** | Step 4b |
| `LogPublishingOptions` missing `SEARCH_SLOW_LOGS` AND `INDEX_SLOW_LOGS` | **CONFIG_GAP** | Step 4c |
| All dimensions clean (CMK at-rest, NTN on, FGAC on, scoped policy, sized masters, slow logs published) | **OK** | Step 5 |

Severity ordering is `NO_ENCRYPTION > PUBLIC_ACCESS > NO_FGAC > CONFIG_GAP > OK`.
Worst finding wins. See the [ordered steps](#process--classification-logic) for
edge cases (VPC domains, AWS-managed CMK, IP-restricted policies).

## Pre-flight: domain shape gate (run before classification)

Several domain attributes **short-circuit** the audit — misjudging them produces
false positives that erode trust.

| Attribute | Value | Effect on audit |
|---|---|---|
| `EngineVersion` | `OpenSearch_X.Y` vs `Elasticsearch_X.Y` | **Elasticsearch legacy.** Still supported but no new features. Note as operational risk, not a verdict driver. |
| `ClusterConfig.DedicatedMasterEnabled` | `false` | No dedicated masters — cluster elects master from data nodes. Step 4b finding (master-node governance gap). |
| `ClusterConfig.DedicatedMasterType` | `t2.small.search` / `t3.small.search` | **Below AWS recommendation** (m5.large.search minimum for masters). Burstable, CPU-credit exhaustion under load causes cluster instability. Step 4b finding. |
| `VPCOptions` | present | **VPC domain.** No internet-facing endpoint. PUBLIC_ACCESS step is skipped — the VPC is the network boundary. FGAC step downgrades to CONFIG_GAP (still recommended, defense-in-depth). |
| `VPCOptions` | absent | **Public endpoint.** Reachable from the internet. PUBLIC_ACCESS and NO_FGAC steps apply at full severity. |
| `Endpoint` / `Endpoints` | used to construct the URL | Endpoint is **immutable**. Changing public-to-VPC or VPC-to-public requires full domain recreation. |
| `EncryptionAtRestOptions.Enabled` | `false` or absent | **NO_ENCRYPTION** — short-circuit Step 1. Data at rest is plaintext. PCI/HIPAA/SOC2 violation. |
| `EncryptionAtRestOptions.KmsKeyId` | AWS-owned default vs customer-CMK | AWS-owned key (`aws/es`) is managed by the service — no customer audit trail, no rotation control, no policy. Note as CONFIG_GAP finding even when `Enabled: true`. |
| `NodeToNodeEncryptionOptions.Enabled` | `false` | Required to enable HTTPS enforcement and FGAC. Cannot be added after domain creation. |
| `DomainEndpointOptions.EnforceHTTPS` | `false` | Allows plaintext HTTP to the data plane. Automatically false when NTN is off (HTTPS enforcement requires NTN). |
| `AdvancedSecurityOptions.Enabled` | `false` | No per-index/per-role/per-user enforcement. The resource policy alone is the access gate. |

**If the input JSON is malformed** (invalid JSON, missing `DomainStatus`),
output:

```text
DOMAIN: <name>
VERDICT: ERROR
REASON: Domain configuration is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws opensearch describe-domain --domain-name <name> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious OpenSearch behaviors that change classification

These behaviors are easy to misjudge without operational OpenSearch experience.
Each changes a verdict if ignored:

- **Encryption-at-rest is IMMUTABLE.** Unlike S3 or EBS, OpenSearch domains
  cannot toggle at-rest encryption after creation. Adding encryption requires
  creating a new domain with `EncryptionAtRestOptions.Enabled: true` and
  re-indexing all data. This is why `Enabled: false` is NO_ENCRYPTION (CRITICAL),
  not CONFIG_GAP — the remediation cost is a full migration, not a config flip.

- **Node-to-node encryption requires HTTPS, and FGAC requires node-to-node.**
  The dependency chain is `HTTPS enforcement → NTN → FGAC`. You cannot enable
  FGAC on a domain where NTN is off. So a `NO_FGAC` finding on a domain with
  `NodeToNodeEncryptionOptions.Enabled: false` has a deeper root cause — fixing
  NTN is a prerequisite to fixing FGAC. State this in the remediation.

- **NTN and at-rest encryption are ALSO immutable post-creation.** Like at-rest,
  node-to-node encryption cannot be toggled on an existing domain. The only
  remediation is domain recreation. The encryption migration is a parallel
  reindex, not an in-place operation.

- **`es:ESHttp*` is the data plane; `es:*` is the full service API.** A
  resource policy granting `es:ESHttp*` to `Principal: "*"` lets any AWS
  account holder read/write/delete every document, index, and template via the
  REST API. `es:*` additionally grants configuration API actions
  (`es:DescribeDomain`, `es:UpdateDomainConfig`) — total domain takeover. Both
  are CRITICAL under PUBLIC_ACCESS, but `es:*` is worse because it enables
  domain reconfiguration (e.g., changing the access policy to a private one
  after exfiltrating data, locking the owner out).

- **`Principal: "*"` with `aws:SourceIp` is NOT a safe pattern for OpenSearch
  public domains.** The standard S3/KMS misconception — "an IP condition
  restricts access" — is more dangerous here because OpenSearch's data plane
  is a REST API. Any caller on a VPN, proxy, or compromised host inside the
  allowed CIDR has full data-plane access. The **only** STRONG condition for a
  public OpenSearch domain is no wildcard principal at all (named ARNs only).
  VPC-backed domains sidestep this entirely.

- **The access policy covers the data plane even when FGAC is on.** FGAC adds
  per-index/per-role enforcement on top of the access policy, but does not
  replace it. A domain with FGAC on AND `Principal: "*"` + `es:ESHttp*` in the
  access policy is still PUBLIC_ACCESS — FGAC does not save you if the
  anonymous caller can satisfy the FGAC master user (e.g., the master is an
  IAM role and the access policy grants `iam:PassRole`-equivalent scope —
  rare, but possible via misconfigured SAML mapping).

- **Dedicated master quorum requires 3 nodes across 3 AZs.** A single
  dedicated master has no HA — a node crash takes the cluster down. AWS
  documentation recommends `m5.large.search` or larger for dedicated masters;
  `t2.small.search` / `t3.small.search` are burstable and run out of CPU
  credits under shard-relocation or snapshot load, causing master-node
  starvation and cluster instability. `DedicatedMasterCount: 1` is a single
  point of failure; `DedicatedMasterCount: 3` with `ZoneAwarenessEnabled: true`
  is the minimum HA posture.

- **Slow log publishing is per-log-type and requires a CloudWatch Logs role
  ARN.** `LogPublishingOptions` is a map of `SEARCH_SLOW_LOGS`,
  `INDEX_SLOW_LOGS`, and `ES_APPLICATION_LOGS` to `{ CloudWatchLogsLogGroupArn, Enabled }`.
  The destination log group must pre-exist and the domain's
  `aws opensearch update-domain-config --log-publishing-options` call requires
  a service-linked role with `logs:CreateLogStream` / `PutLogEvents`. Missing
  slow logs means slow queries (>5s by default) are invisible — production
  incidents go undiagnosed.

- **The slow-log thresholds (0-100ms index, 0-1000ms search by default) are
  NOT emitted in describe-domain output.** They live in cluster settings
  (`_cluster/settings`) — only reachable via the data plane. The audit can
  flag absence of publishing, but cannot determine threshold calibration from
  configuration API alone. State this limitation in the FINDINGS note.

- **Domain endpoint URL is sensitive.** `https://<domain-id>.<region>.es.amazonaws.com`
  is a public DNS record for internet-facing domains. Anyone who learns the
  endpoint can attempt REST API calls; the access policy is the only gate. A
  leaked endpoint combined with a permissive policy is a data breach. VPC
  domains use a private DNS name resolvable only inside the VPC.

- **AWS-managed KMS key (`aws/es`) is owned by the service.** The customer
  cannot audit CloudTrail for `kms:Decrypt` calls against it (the service
  opaque-wraps the call), cannot rotate the key material on demand, and cannot
  apply a customer key policy. A customer-managed CMK provides full audit
  trail and rotation control. Treat `aws/es` as a CONFIG_GAP finding even when
  encryption is enabled — it is technically encrypted but operationally
  opaque.

- **FGAC master user can be IAM or internal.** When
  `AdvancedSecurityOptions.InternalUserDatabaseEnabled: true`, the master is a
  username/password created at enablement time. When false, the master is the
  IAM ARN in `MasterUserOptions.MasterUserARN`. Loss of the internal master
  password is unrecoverable without disabling and re-enabling FGAC (a
  destructive operation). Flag `InternalUserDatabaseEnabled: true` as a
  CONFIG_GAP finding if the master credentials are not in Secrets Manager.

- **Additional operational deltas (CCS, CCR, engine-version lifecycle, serverless
  boundary) are in [Deep reference: operational deltas](#deep-reference-operational-deltas)
  — consult when auditing cross-cluster, replication, or legacy-Elasticsearch domains.

### Step 1: Encryption-at-rest (highest priority — NO_ENCRYPTION)

Evaluate `EncryptionAtRestOptions`:

- **`Enabled: false` or absent** → **NO_ENCRYPTION** (CRITICAL). Data at rest
  is plaintext. Every snapshot, every EBS volume backing the data nodes, and
  every automated backup is plaintext. PCI-DSS 3.4, HIPAA 164.312(a)(2)(iv),
  and SOC2 CC6.1 all require encryption-at-rest for in-scope data — this is
  a hard compliance stop. The remediation is **always** domain recreation
  (encryption is immutable); do not emit "enable encryption" guidance.

- **`Enabled: true` + `KmsKeyId: aws/es` (or absent)** → Encryption is on but
  uses the AWS-owned/AWS-managed key. Note as a CONFIG_GAP finding
  (`[CONFIG_GAP] Encryption uses AWS-managed key aws/es — no customer audit
  trail, no rotation control, no customer key policy`). Does not change the
  verdict on its own (CONFIG_GAP is additive to other findings).

- **`Enabled: true` + customer-managed `KmsKeyId` (CMK ARN)** → OK on this
  dimension. The CMK provides CloudTrail Decrypt logging, customer-controlled
  rotation, and a customer-authored key policy.

NO_ENCRYPTION short-circuits to Step 5 (aggregation). All other dimensions are
still evaluated and listed in FINDINGS, but the verdict is already determined.

### Step 2: Public access via resource policy (PUBLIC_ACCESS)

For each `Effect: Allow` statement in the access policy, classify the principal
and the action set.

**Principal scope:**
- **WILDCARD_PRINCIPAL** — `Principal: "*"`, `Principal: {"AWS": "*"}`, or
  `Principal: {"Service": "*"}`.
- **CROSS_ACCOUNT** — principal ARN's 12-digit account ID differs from the
  domain's owning account.
- **SAME_ACCOUNT** — all principals share the owning account ID (including
  account root).

**Action danger:**
- **DATA_PLANE** — `es:ESHttp*`, `es:*`, `es:HttpGet`, `es:ESHttpPost`,
  `es:ESHttpPut`, `es:ESHttpDelete`. These reach the OpenSearch REST API
  (read/write every document).
- **CONFIGURATION_PLANE** — `es:DescribeDomain`, `es:ListDomainNames`,
  `es:UpdateDomainConfig`. Information disclosure and reconfiguration.
- **read-only DATA_PLANE** — `es:ESHttpGet` only (read documents).

**Condition strength:**
- **STRONG** — `aws:SourceArn` with `StringEquals` (specific resource),
  `aws:SourceAccount` with `StringEquals` (specific account). These are set by
  AWS service infrastructure and not caller-controlled.
- **WEAK** — `aws:SourceIp` with a non-`0.0.0.0/0` CIDR. Real CIDR but
  bypassable by VPN/NAT/proxy. Treat as a partial restriction, not a hard
  boundary.
- **NONE** — no condition, or `aws:SourceIp: 0.0.0.0/0`.

**Step 2 verdict matrix** (skip for VPC domains — no internet endpoint):

| # | Principal | Action | Condition | Verdict |
|---|---|---|---|---|
| 2a | WILDCARD | DATA_PLANE / `es:*` | None/Weak | **PUBLIC_ACCESS** |
| 2b | WILDCARD | DATA_PLANE | Strong (`aws:SourceAccount`/`aws:SourceArn`) | Downgrade — see Step 3 (still NO_FGAC if FGAC off) |
| 2c | CROSS_ACCOUNT | DATA_PLANE | None/Weak | **PUBLIC_ACCESS** (external account has data-plane access) |
| 2d | WILDCARD/CROSS | CONFIGURATION_PLANE only | None/Weak | **CONFIG_GAP** (metadata leak; cannot read data) |
| 2e | WILDCARD/CROSS | Any | Strong | Downgrade one level |
| 2f | SAME_ACCOUNT | Any | Any | OK on this dimension (no public exposure) |

A statement with both `Principal: "*"` and a STRONG condition is rare and
fragile — flag as currently restricted but document that a single policy edit
removes the restriction.

### Step 3: Fine-grained access control (NO_FGAC)

Evaluate `AdvancedSecurityOptions.Enabled`:

- **`Enabled: false` + internet-facing domain (no VPCOptions)** → **NO_FGAC**
  (HIGH). Without FGAC, the resource policy alone determines access. Any
  principal with `es:ESHttp*` (same-account role, IP-restricted wildcard, etc.)
  has unrestricted access to every index — there is no per-index role, no
  document-level security, no field masking. The remediation prerequisite is
  NTN (Step 4a) — flag the dependency.

- **`Enabled: false` + VPC domain** → **CONFIG_GAP** (MEDIUM). The VPC is the
  network boundary, reducing exposure. But defense-in-depth still recommends
  FGAC for blast-radius containment (a compromised EC2 in the VPC has full
  data-plane access without FGAC).

- **`Enabled: true`** → OK on this dimension. Validate that
  `InternalUserDatabaseEnabled` is not the only auth path (a lost master
  password is unrecoverable). Flag as CONFIG_GAP finding if the master
  credentials are not stored in Secrets Manager.

### Step 4: Configuration gaps (CONFIG_GAP)

Each finding is additive. None changes the verdict on its own (a CONFIG_GAP
finding adds to the FINDINGS list; the verdict is driven by Steps 1-3).

**Step 4a: Node-to-node encryption**
- `NodeToNodeEncryptionOptions.Enabled: false` → CONFIG_GAP finding.
  Inter-node traffic is plaintext. Required for FGAC and HTTPS enforcement.
  Immutable post-creation.

**Step 4b: Dedicated master node type and count**
- `DedicatedMasterEnabled: false` → CONFIG_GAP finding. Cluster elects master
  from data nodes — master election storms under node churn.
- `DedicatedMasterCount: 1` → CONFIG_GAP finding. Single point of failure.
- `DedicatedMasterType: t2.small.search` or `t3.small.search` → CONFIG_GAP
  finding. Below AWS recommendation (`m5.large.search` minimum). Burstable;
  CPU-credit exhaustion destabilises master.
- `DedicatedMasterCount: 2` → CONFIG_GAP finding. Even counts cannot form
  quorum. AWS requires 3 for HA.

**Step 4c: Slow log publishing**
- `LogPublishingOptions.SEARCH_SLOW_LOGS.Enabled: false` or absent → CONFIG_GAP
  finding. Slow queries invisible.
- `LogPublishingOptions.INDEX_SLOW_LOGS.Enabled: false` or absent → CONFIG_GAP
  finding. Slow indexing invisible.
- Note: threshold calibration (`index.search.slowlog.threshold.warn`, etc.)
  lives in cluster settings, not in describe-domain output. Flag the
  publishing gap; cannot audit thresholds from configuration API.

**Step 4d: HTTPS enforcement**
- `DomainEndpointOptions.EnforceHTTPS: false` → CONFIG_GAP finding. Allows
  plaintext HTTP to the data plane. Automatically false when NTN is off.

**Step 4e: AWS-managed KMS key**
- `EncryptionAtRestOptions.KmsKeyId` is `aws/es` or absent → CONFIG_GAP finding.
  Customer cannot audit, rotate, or apply a key policy.

### Step 5: Aggregation — worst finding wins

```text
verdict = max(step1_verdict, step2_verdict, step3_verdict, step4_findings)
```

Precedence: `NO_ENCRYPTION > PUBLIC_ACCESS > NO_FGAC > CONFIG_GAP > OK`.
All findings from all steps are listed in FINDINGS; the verdict is the worst
single step's verdict. If no findings (all dimensions OK), verdict is **OK**.

## Output format (per domain)

```text
DOMAIN: <domain-name>
VERDICT: NO_ENCRYPTION | PUBLIC_ACCESS | NO_FGAC | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step 1a)>
  - [CONFIG_GAP] <finding description (Step 4a)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — public wildcard + FGAC off + AWS-managed key

```text
DOMAIN: logs-prod
VERDICT: PUBLIC_ACCESS
REASON: Access policy Statement "OpenAccess" grants es:ESHttp* to Principal
"*" with no restrictive condition (Step 2a) — any AWS account holder can
read/write every document and delete every index. FGAC is also disabled,
compounding the data-plane exposure.
FINDINGS:
  - [PUBLIC_ACCESS] Principal "*" + es:ESHttp* with no condition (Step 2a)
  - [NO_FGAC] AdvancedSecurityOptions.Enabled is false on an internet-facing
    domain (Step 3a)
  - [CONFIG_GAP] EncryptionAtRestOptions.KmsKeyId is aws/es — AWS-managed key,
    no customer audit trail (Step 4e)
  - [OK] NodeToNodeEncryptionOptions.Enabled is true (Step 4a)
REMEDIATION:
  1. PUBLIC_ACCESS — Immediately remove the wildcard principal. Replace with
     named ARNs or restrict via aws:SourceAccount. Back up the policy first:
     aws opensearch describe-domain-access-policy --domain-name logs-prod >
     /tmp/logs-prod-policy-backup.json.
  2. Assume breach. Audit CloudTrail for es:ESHttp* calls from external
     principals during the exposure window. Reindex compromised data into a
     fresh domain.
  3. NO_FGAC — Prerequisite: NTN must be on (it is). Enable FGAC:
     aws opensearch update-domain-config --domain-name logs-prod
     --advanced-security-options 'Enabled=true,InternalUserDatabaseEnabled=false,MasterUserOptions={MasterUserARN=arn:aws:iam::111111111111:role/opensearch-master}'
  4. CONFIG_GAP — Plan a migration to a customer-managed CMK for at-rest
     encryption (requires domain recreation).
```

## Edge-case handling

- **Empty access policy.** A domain with no resource policy uses account-level
  IAM as the gate. For internet-facing domains, this is the AWS default
  posture (the account root can call es:* but no one else can). Note as OK on
  Step 2; do NOT flag as PUBLIC_ACCESS.

- **`Principal: "*"` with `aws:SourceIp` covering a corporate CIDR.** This is
  the legacy "office IP allowlist" pattern. Treat as WEAK — bypassable by VPN.
  Verdict is PUBLIC_ACCESS (Step 2a) unless FGAC is on AND the access policy
  has no DATA_PLANE wildcard; otherwise NO_FGAC. Document the bypass risk in
  the FINDINGS note.

- **VPC domain with wildcard principal.** VPC endpoints are not internet-
  facing, so PUBLIC_ACCESS does not apply. However, the wildcard principal
  means anyone inside the VPC has data-plane access. Flag as NO_FGAC if FGAC
  is off (the VPC boundary is not per-index enforcement), else CONFIG_GAP.

- **Access policy with `Principal: {"Service": "es.amazonaws.com"}`.** This is
  a service-principal grant for OpenSearch-to-OpenSearch calls (e.g., cross-
  cluster search). Classify as SAME_ACCOUNT/OK unless the policy also has
  `Principal: "*"`.

- **DedicatedMasterCount: 2.** Even counts cannot form quorum (3 is minimum).
  AWS rejects DedicatedMasterCount: 2 at creation, but legacy domains may
  have it via direct API manipulation. Flag as CONFIG_GAP — cluster cannot
  achieve HA quorum.

- **`ClusterConfig.InstanceType: t3.small.search` for data nodes.** Burstable
  data nodes run out of CPU credits under indexing load. Not a verdict driver
  but note as an operational risk if the domain handles production traffic.

- **Multi-AZ without `ZoneAwarenessEnabled: true`.** A multi-node cluster
  without zone awareness deploys all nodes in one AZ — an AZ failure takes
  the cluster down. Flag as CONFIG_GAP when `InstanceCount >= 2` and
  `ZoneAwarenessEnabled: false`.

## Anti-Patterns — NEVER

- NEVER recommend "enable encryption-at-rest" as an in-place fix.
  OpenSearch at-rest encryption is **immutable** post-creation. The only
  remediation is creating a new encrypted domain and reindexing. Stating
  otherwise is operationally misleading and erodes operator trust.

- NEVER recommend "enable node-to-node encryption" as an in-place fix either.
  NTN is **also immutable** post-creation. Same remediation path: domain
  recreation. Confusing NTN with KMS at-rest (which can be toggled for some
  services) is a common auditor mistake.

- NEVER classify a VPC-backed domain as PUBLIC_ACCESS regardless of access
  policy. VPC endpoints are not internet-reachable; the VPC security group
  and route table are the network boundary. The access policy is still
  audited (a `Principal: "*"` on a VPC domain is still NO_FGAC if FGAC is
  off), but the PUBLIC_ACCESS verdict does not apply.

- NEVER treat `aws:SourceIp` with a real CIDR as a STRONG condition for an
  OpenSearch public domain. IP-based restrictions are bypassable by VPN,
  NAT, or proxy. The only STRONG conditions for OpenSearch are
  `aws:SourceArn` and `aws:SourceAccount` set by AWS service infrastructure.
  Treating IP CIDR as STRONG produces false-safe PUBLIC_ACCESS
  classifications.

- NEVER flag `EncryptionAtRestOptions.Enabled: true` with `aws/es` as
  NO_ENCRYPTION. The data IS encrypted — the gap is customer control (audit
  trail, rotation, key policy), not plaintext storage. This is a CONFIG_GAP
  finding, not a CRITICAL verdict. Confusing the two erodes trust in the
  auditor.

- NEVER assume FGAC is on because the access policy is restrictive. FGAC is
  an **independent** layer from the access policy. A domain with a tightly
  scoped access policy but `AdvancedSecurityOptions.Enabled: false` still has
  no per-index/per-role enforcement — any allowed principal has full data-
  plane access. Always check `AdvancedSecurityOptions.Enabled` separately.

- NEVER enable FGAC without first verifying NTN is on and HTTPS enforcement
  is on. FGAC requires NTN, and NTN requires HTTPS. A `update-domain-config`
  call to enable FGAC on a domain with NTN off returns
  `ValidationException`. Surface this prerequisite in the remediation.

- NEVER recommend a single dedicated master for HA. OpenSearch master
  election requires a quorum (majority of masters). Three dedicated masters
  across three AZs is the minimum HA posture. `DedicatedMasterCount: 1` is a
  single point of failure; `DedicatedMasterCount: 2` cannot form quorum.

- NEVER classify `t2.small.search` or `t3.small.search` as adequate for
  dedicated masters on production domains. AWS recommends `m5.large.search`
  or larger. Burstable instance types exhaust CPU credits under shard
  relocation / snapshot load, causing master starvation and cluster
  instability. Always flag below-m5 dedicated masters.

- NEVER overlook `LogPublishingOptions` absence. Slow logs are the primary
  diagnostic for production OpenSearch incidents (slow queries, slow
  indexing). Without `SEARCH_SLOW_LOGS` and `INDEX_SLOW_LOGS` published to
  CloudWatch Logs, the operator has no visibility into which queries are
  degrading — incidents go undiagnosed.

- NEVER conflate OpenSearch Service with OpenSearch Serverless. Serverless
  collections have different APIs (`aoss:API*`), different encryption
  semantics (always encrypted, no toggle), and different capacity models
  (OCU). This skill's logic applies to provisioned OpenSearch Service only.

- NEVER treat the account-root statement in the access policy
  (`Principal: {"AWS": "arn:aws:iam::ACCOUNT:root"}` + `es:*`) as
  WILDCARD_PRINCIPAL. This is the standard IAM-delegation pattern and is
  NORMAL. Classify as SAME_ACCOUNT / OK.

- NEVER treat `Principal: "*"` with `es:DescribeDomain*` only as PUBLIC_ACCESS.
  Describe actions reveal domain metadata (name, ARN, endpoint, config) but
  cannot read documents. Flag as CONFIG_GAP (information disclosure), not
  PUBLIC_ACCESS (data exposure). The PUBLIC_ACCESS verdict is reserved for
  data-plane or full-service-API exposure.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-domain-config`, `update-domain-access-policy`, `delete-domain`,
  `create-domain`), emit
  `CONFIRM: About to <action> on domain <name>. This affects <consequence>. Proceed? (yes/no)`.
  Do NOT execute the CLI command until the operator confirms.
- **Back up the access policy** before any change:
  `aws opensearch describe-domain-access-policy --domain-name <name> --output json > /tmp/<name>-policy-backup-$(date +%s).json`.
  Access policy changes are not versioned.
- **Snapshot before encryption migration.** A domain recreation without a
  snapshot loses all data. Take a manual snapshot to S3 first:
  ```
  PUT _snapshot/<repo-name>/<snapshot-name> { "indices": "*" }
  ```
  The snapshot repository must be registered in the new domain before
  restore.
- **Verify the caller's identity** can run `opensearch:UpdateDomainConfig` if
  remediation is intended — most read-only auditor roles cannot, and
  remediation commands fail with `AccessDeniedException`.
- **Blue/green cost spike warning.** `update-domain-config` triggers a
  blue/green deployment that provisions a parallel fleet of nodes before
  decommissioning the old one — cost briefly doubles. Surface this in the
  CONFIRMATION gate.
- **Do NOT disable FGAC as a remediation step** without operator approval.
  Disabling FGAC removes all per-index controls. The only safe path is
  additively fixing the underlying config (rotate master, update role
  mappings).

## Remediation guidance

### For NO_ENCRYPTION — at-rest encryption off (Step 1a)

1. **Verify no live data dependencies** — CloudTrail `es:ESHttp*` events,
   application logs referencing the endpoint.
2. **Take a manual snapshot** to S3 (registered repo required).
3. **Create a new encrypted domain** with the same engine version, instance
   type, and CMK ARN:
   ```
   aws opensearch create-domain --domain-name <name>-encrypted \
     --engine-version OpenSearch_2.11 \
     --cluster-config InstanceType=m5.large.search,InstanceCount=3 \
     --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=100 \
     --encryption-at-rest-options Enabled=true,KmsKeyId=arn:aws:kms:...:key/<cmk> \
     --node-to-node-encryption-options Enabled=true
   ```
4. **Restore the snapshot** to the new domain.
5. **Repoint clients** to the new endpoint. The endpoint URL changes — no
   in-place swap is possible.
6. **Schedule deletion** of the old domain only after the new domain is
   verified.

### For PUBLIC_ACCESS — wildcard/cross-account data-plane grant (Step 2a)

1. **Immediately remove the wildcard principal** from the access policy, or
   add a STRONG condition (`aws:SourceAccount`, `aws:SourceArn`).
2. **Assume breach.** Audit CloudTrail for `es:ESHttp*` events from external
   principals during the exposure window. Reindex any compromised indices
   into a fresh domain.
3. If public read is **intentional** (e.g., public dashboard), replace
   `Principal: "*"` with `Principal: "*"` + `aws:SourceIp` of the corporate
   CIDR AND enable FGAC with anonymous-readonly role — never grant
   `es:ESHttpDelete` or `es:ESHttpPut` to a wildcard.

### For NO_FGAC — fine-grained access control off (Step 3a)

1. **Prerequisite: verify NTN is on and HTTPS is enforced.**
   `aws opensearch describe-domain-config --domain-name <name>` and check
   `NodeToNodeEncryptionOptions.Enabled` and
   `DomainEndpointOptions.EnforceHTTPS`. If either is off, plan a domain
   recreation (NTN is immutable).
2. **Enable FGAC** with IAM master (recommended over internal user database):
   ```
   aws opensearch update-domain-config --domain-name <name> \
     --advanced-security-options 'Enabled=true,InternalUserDatabaseEnabled=false,MasterUserOptions={MasterUserARN=arn:aws:iam::111111111111:role/opensearch-master}'
   ```
3. **Define roles** via the Security plugin REST API (`_plugins/_security/api/roles/`).
4. **Map roles** to IAM principals via `_plugins/_security/api/rolesmapping/`.

### For CONFIG_GAP — additive findings (Step 4)

- **NTN off (Step 4a)**: Plan domain recreation with NTN enabled.
- **Master node type/size (Step 4b)**: `update-domain-config --cluster-config
  DedicatedMasterEnabled=true,DedicatedMasterType=m5.large.search,DedicatedMasterCount=3`.
  Triggers blue/green.
- **Slow logs (Step 4c)**: Create the destination log groups first, then
  `update-domain-config --log-publishing-options
  SEARCH_SLOW_LOGS={CloudWatchLogsLogGroupArn=arn:aws:logs:...,Enabled=true},
  INDEX_SLOW_LOGS={CloudWatchLogsLogGroupArn=arn:aws:logs:...,Enabled=true}`.
- **HTTPS enforcement off (Step 4d)**: `update-domain-config
  --domain-endpoint-options EnforceHTTPS=true`. Requires NTN to be on.
- **AWS-managed key (Step 4e)**: Plan a CMK migration (domain recreation).

### For OK

1. No remediation required for the current posture.
2. Validate that the CMK rotation is enabled (`aws kms get-key-rotation-status
   --key-id <cmk>`).
3. Validate that the dedicated master count is 3 and the type is m5 or larger.
4. Review slow-log thresholds via `_cluster/settings` (data-plane call).

## Deep reference: operational deltas

These bullets expand on Step 0 with operational behaviors that change the audit
for cross-cluster, replication, or legacy-engine domains. Read this section
when the input domain has any of those characteristics.

- **Multi-tenant OpenSearch Serverless is a different product.** This skill
  is for provisioned OpenSearch Service domains. Serverless collections have
  different APIs (`aoss:API*` actions), encryption models, and capacity
  semantics — do not apply this skill's logic to Serverless.

- **Cross-cluster search (CCS) re-opens the access-policy boundary.** When a
  domain is registered as a remote in another domain's `_cluster/settings`
  (the `cluster.remote.<alias>.seeds` setting), the local domain's access
  policy does NOT gate the remote caller — the connection is authenticated
  at the cluster level, not per-request. A "sanitized" local domain that
  queries a hardened remote inherits the remote's data without the remote's
  FGAC role-mapping being enforced (FGAC is NOT propagated across CCS — the
  querying cluster runs as the connection principal, not as the end user).
  Flag CCS wiring as a CONFIG_GAP finding if any remote is registered — the
  audit must cover the connection's auth mode (no-auth vs signature) and
  whether the remote trusts the local cluster's identity.

- **Engine version deprecation follows a published lifecycle.** AWS
  announces OpenSearch version deprecations on a 12-month cadence; once a
  version enters the deprecation window, `create-domain` for that
  EngineVersion is blocked, then 6 months later `update-domain-config` on
  existing domains is blocked, then 12 months later the domain is force-
  upgraded. `Elasticsearch_*` engine versions are permanently in deprecation
  (no new features since the OpenSearch fork) — flag any
  `EngineVersion: Elasticsearch_X.Y` as a CONFIG_GAP finding (operational
  risk: feature drift, talent attrition, eventual forced upgrade) regardless
  of other findings. The skill cannot read the deprecation calendar from
  describe-domain output — surface this as a static rule.

- **Cross-cluster replication (CCR) has the inverse security property of
  CCS.** CCR replicates indices FROM a leader TO a follower cluster. The
  follower needs `indices:admin/index_template/create` and
  `indices:data/write/index` on the leader — a follower with these
  permissions can mutate leader mappings. Treat any domain with the
  `replication` plugin enabled as elevated write-surface; flag as CONFIG_GAP
  if the follower's role ARN is not in the access policy.

## Deep reference: OpenSearch encryption dependency chain

```
At-rest encryption (immutable, KMS)
        |
        v
Node-to-node encryption (immutable, requires HTTPS)
        |
        v
HTTPS enforcement (mutable once NTN is on)
        |
        v
FGAC / Advanced Security (mutable, requires NTN + HTTPS)
        |
        v
Per-index roles, document-level security, field masking
```

Each layer depends on the layer above. A domain missing the top layer
(at-rest) cannot have any layer below. A domain missing NTN cannot have HTTPS
enforcement or FGAC. This is why the verdict precedence is
`NO_ENCRYPTION > PUBLIC_ACCESS > NO_FGAC > CONFIG_GAP` — fixing a higher
verdict often requires fixing all lower layers simultaneously during a domain
recreation.

## Domain

AWS CloudOps / OpenSearch Analytics Security & Compliance.
