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
version: 0.3.0
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

## Quick start

Invoke when classifying an OpenSearch Service (provisioned) domain against the
**AWS Security Hub Foundational Security Best Practices (FSBP)** controls
OS.1–OS.8. Minimal live-account invocation:

```text
Audit OpenSearch domain "logs-prod" in us-east-1.
aws opensearch describe-domain --domain-name logs-prod
aws opensearch describe-domain-config --domain-name logs-prod
aws opensearch describe-domain-access-policy --domain-name logs-prod
```

The verdict is the **worst** finding:
`NO_ENCRYPTION > PUBLIC_ACCESS > NO_FGAC > CONFIG_GAP > OK`.
Apply [Process](#process--classification-logic) steps in order. Edge cases,
anti-patterns, and operational insights are in [Reference](#reference).

## Critical rule — confirmation gate

Every state-changing remediation (`update-domain-config`,
`update-domain-access-policy`, `delete-domain`, `create-domain`) is **blocked**
until the operator confirms. Emit and halt:

```text
CONFIRM: About to <action> on domain <name>. This affects <consequence>. Proceed? (yes/no)
```

This gate is **non-negotiable** and applies to **every** remediation command
without exception — including log-publishing updates, master-node resize,
HTTPS-enforcement toggles, and access-policy edits. OpenSearch mutations can
take 30 minutes to several hours (blue/green deployment that doubles node
count — cost spike), and some changes (encryption-at-rest, NTN, VPC-vs-public
endpoint) are **immutable** and require full domain recreation. Do not
batch-confirm; prompt once per action.

## Decision tree — severity thresholds

| Condition | Verdict | Step | FSBP |
|---|---|---|---|
| `EncryptionAtRestOptions.Enabled: false` (or absent) | **NO_ENCRYPTION** | 1a | OS.1 |
| `Principal: "*"` + `es:ESHttp*`/`es:*` + no STRONG condition (non-VPC) | **PUBLIC_ACCESS** | 2a | OS.3 |
| `Principal: "*"` + DATA_PLANE + STRONG (`aws:SourceAccount`/`aws:SourceArn`) | Downgrade (NO_FGAC if FGAC off) | 2b | OS.3 |
| `AdvancedSecurityOptions.Enabled: false` on internet-facing domain | **NO_FGAC** | 3a | OS.3 |
| `AdvancedSecurityOptions.Enabled: false` on VPC domain | **CONFIG_GAP** | 3b | OS.4 |
| `NodeToNodeEncryptionOptions.Enabled: false` (at-rest on) | **CONFIG_GAP** | 4a | OS.2/OS.8 |
| Dedicated master `t2/t3.small.search`, count 1/2, or none | **CONFIG_GAP** | 4b | — |
| `LogPublishingOptions` missing `SEARCH_SLOW_LOGS` AND `INDEX_SLOW_LOGS` | **CONFIG_GAP** | 4c | OS.6/OS.7 |
| `DomainEndpointOptions.EnforceHTTPS: false` | **CONFIG_GAP** | 4d | OS.5 |
| `KmsKeyId` is `aws/es` or absent | **CONFIG_GAP** | 4e | OS.1 |
| `InstanceCount >= 2` + `ZoneAwarenessEnabled: false` | **CONFIG_GAP** | 4f | — |
| `EngineVersion: Elasticsearch_X.Y` (legacy fork) | **CONFIG_GAP** | 4g | — |
| All dimensions clean | **OK** | 5 | — |

Worst finding wins. VPC domains skip Step 2 (no internet endpoint).

## Mindset

OpenSearch is unusual among AWS data services: the resource-based policy gates
**both** the configuration API (`es:DescribeDomain`) and the data plane
(`es:ESHttp*` — full REST API: read every document, delete every index, change
every mapping). A pattern safe for S3 or KMS (`Principal: "*"` with
`aws:SourceIp`) is **not** safe for OpenSearch — `aws:SourceIp` is bypassable
via VPN/NAT and there are no per-object ACLs as a fallback.

Three counter-intuitive facts drive most misclassifications:
(1) encryption-at-rest and node-to-node encryption are both **immutable**
post-creation — no toggle, the remediation is a full reindex migration;
(2) FGAC cannot be enabled without NTN, which requires HTTPS — so a `NO_FGAC`
finding often hides a deeper immutable NTN root cause;
(3) the access policy is evaluated **before** FGAC, so a wildcard principal
grants data-plane access even when FGAC is on.

## Process — Classification logic

Apply in order, aggregate worst. See [Reference](#reference) for the
operational reasoning behind each rule.

### Step 1: Encryption-at-rest (NO_ENCRYPTION)

- **`Enabled: false` or absent** → **NO_ENCRYPTION** (CRITICAL). Data at rest
  is plaintext — every snapshot, EBS volume, and backup. PCI-DSS 3.4, HIPAA
  164.312(a)(2)(iv), SOC2 CC6.1 violation. Remediation is **always** domain
  recreation (encryption is immutable); do not emit "enable encryption"
  guidance. Short-circuits to Step 5.
- **`Enabled: true` + `KmsKeyId: aws/es` or absent** → CONFIG_GAP finding. The
  AWS-OWNED key `aws/es` is opaque: no CloudTrail `kms:Decrypt` events (the
  service calls Decrypt on its own principal), no rotation control, no customer
  key policy. See [Reference: aws/es opacity](#awses-cloudtrail-opacity).
- **`Enabled: true` + customer-managed CMK ARN** → OK on this dimension.

### Step 2: Public access via resource policy (PUBLIC_ACCESS)

Skip for VPC domains. For each `Effect: Allow` statement, classify:

- **Principal**: WILDCARD (`"*"`, `{"AWS": "*"}`, `{"Service": "*"}`) |
  CROSS_ACCOUNT (different 12-digit account) | SAME_ACCOUNT.
- **Action**: DATA_PLANE (`es:ESHttp*`, `es:*`, `es:ESHttpGet/Post/Put/Delete`) |
  CONFIGURATION_PLANE (`es:Describe*`, `es:UpdateDomainConfig`) |
  read-only DATA_PLANE (`es:ESHttpGet` only).
- **Condition**: STRONG (`aws:SourceArn`/`aws:SourceAccount` with
  `StringEquals` — set by AWS infrastructure, not caller-controlled) |
  WEAK (`aws:SourceIp` with real CIDR — bypassable by VPN/NAT/proxy) |
  NONE (no condition, or `0.0.0.0/0`).

| # | Principal | Action | Condition | Verdict |
|---|---|---|---|---|
| 2a | WILDCARD | DATA_PLANE / `es:*` | None/Weak | **PUBLIC_ACCESS** |
| 2b | WILDCARD | DATA_PLANE | Strong | Downgrade (NO_FGAC if FGAC off) |
| 2c | CROSS_ACCOUNT | DATA_PLANE | None/Weak | **PUBLIC_ACCESS** |
| 2d | WILDCARD/CROSS | CONFIGURATION_PLANE only | None/Weak | **CONFIG_GAP** (metadata leak) |
| 2e | WILDCARD/CROSS | Any | Strong | Downgrade one level |
| 2f | SAME_ACCOUNT | Any | Any | OK |

The account-root statement (`Principal: {"AWS": "arn:aws:iam::ACCOUNT:root"}`
+ `es:*`) is the standard IAM-delegation pattern — classify as SAME_ACCOUNT/OK.

### Step 3: Fine-grained access control (NO_FGAC)

- **`Enabled: false` + internet-facing (no VPCOptions)** → **NO_FGAC** (HIGH).
  Without FGAC, the resource policy alone determines access. Any principal
  with `es:ESHttp*` has unrestricted access to every index — no per-index
  role, no document-level security, no field masking. Remediation prerequisite
  is NTN (Step 4a) — flag the dependency.
- **`Enabled: false` + VPC domain** → **CONFIG_GAP** (MEDIUM). VPC is the
  network boundary, reducing exposure. But defense-in-depth still recommends
  FGAC for blast-radius containment.
- **`Enabled: true`** → OK. Flag CONFIG_GAP finding if
  `InternalUserDatabaseEnabled: true` and master credentials are not in Secrets
  Manager (loss of internal master password is unrecoverable without disabling
  FGAC — a destructive operation that wipes all role mappings).

### Step 4: Configuration gaps (CONFIG_GAP — additive)

Each finding adds to FINDINGS; none changes the verdict on its own.

- **4a NTN off**: `NodeToNodeEncryptionOptions.Enabled: false`. Inter-node
  traffic plaintext. Required for FGAC and HTTPS. **Immutable** post-creation —
  domain recreation only.
- **4b Master node**: `DedicatedMasterEnabled: false` (election storms);
  `DedicatedMasterCount: 1` (SPOF) or `2` (no quorum — AWS requires 3 for HA);
  `DedicatedMasterType: t2/t3.small.search` (below m5.large.search minimum,
  CPU-credit exhaustion silently drops cluster-state API calls). Master
  type/count IS mutable via `update-domain-config` (blue/green).
- **4c Slow logs**: `SEARCH_SLOW_LOGS` or `INDEX_SLOW_LOGS` absent/disabled.
  Slow queries invisible. Threshold calibration lives in `_cluster/settings`,
  not describe output.
- **4d HTTPS off**: `EnforceHTTPS: false`. Plaintext HTTP to data plane.
  Auto-false when NTN off. Mutable.
- **4e AWS-managed key**: `KmsKeyId` is `aws/es` or absent. No customer audit
  trail, rotation, or key policy. Migration requires domain recreation.
- **4f Single-AZ multi-node**: `InstanceCount >= 2` + `ZoneAwarenessEnabled:
  false`. All nodes in one AZ — AZ failure takes cluster down.
- **4g Legacy engine**: `EngineVersion: Elasticsearch_X.Y`. No new features
  since fork; eventual forced upgrade. Not a verdict driver but always emit.

### Step 5: Aggregation

Precedence: `NO_ENCRYPTION > PUBLIC_ACCESS > NO_FGAC > CONFIG_GAP > OK`. All
findings listed in FINDINGS; verdict is the worst single step's verdict.

## Output format (per domain)

Emit one block per domain in this field order. For batch/multi-domain input,
process each independently — emit blocks sequentially. If one domain errors,
emit its ERROR block and continue.

```text
DOMAIN: <domain-name>
VERDICT: NO_ENCRYPTION | PUBLIC_ACCESS | NO_FGAC | CONFIG_GAP | OK | ERROR
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [SEVERITY] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

**Immutable-vs-mutable scope:** Only at-rest encryption (Step 1a) and NTN
(Step 4a) require **domain recreation** — state "requires domain recreation
(immutable)" for these. Master-node type/count (Step 4b), HTTPS (Step 4d),
slow-log publishing (Step 4c), and FGAC (Step 3) ARE mutable in-place via
`update-domain-config` (blue/green deployment) — state "in-place via
update-domain-config" for these. Never confuse the two.

**Error handling:** If input JSON is invalid, missing `DomainStatus`, or the
access-policy fetch failed, emit `VERDICT: ERROR` with the specific cause. If
the API returns `ThrottlingException`, retry once with exponential backoff; if
`AccessDeniedException`, state the required IAM permission. Do NOT fabricate a
verdict on API failure.

### Worked example — public wildcard + FGAC off

```text
DOMAIN: logs-prod
VERDICT: PUBLIC_ACCESS
REASON: Access policy grants es:ESHttp* to Principal "*" with no restrictive
condition (Step 2a) — any AWS account holder can read/write every document.
FGAC is also disabled, compounding the exposure.
FINDINGS:
  - [PUBLIC_ACCESS] Principal "*" + es:ESHttp* with no condition (Step 2a)
  - [NO_FGAC] AdvancedSecurityOptions.Enabled is false on internet-facing domain (Step 3a)
  - [CONFIG_GAP] KmsKeyId is aws/es — no CloudTrail audit trail (Step 4e)
  - [OK] NodeToNodeEncryptionOptions.Enabled is true (Step 4a)
REMEDIATION:
  1. PUBLIC_ACCESS — Remove wildcard principal. Replace with named ARNs or
     aws:SourceAccount. Back up policy first (NOT versioned — no rollback):
     aws opensearch describe-domain-access-policy --domain-name logs-prod > /tmp/logs-prod-policy-backup.json
  2. Assume breach. Audit CloudTrail for es:ESHttp* from external principals.
  3. NO_FGAC — In-place via update-domain-config (blue/green): enable FGAC with
     IAM master:
     aws opensearch update-domain-config --domain-name logs-prod
       --advanced-security-options 'Enabled=true,InternalUserDatabaseEnabled=false,MasterUserOptions={MasterUserARN=arn:aws:iam::111111111111:role/opensearch-master}'
  4. CONFIG_GAP — Plan CMK migration: requires domain recreation (immutable).
```

## Reference

Consult when the audit hits an edge case. These operational behaviors are NOT
in AWS documentation and change classification if ignored.

### Pre-flight: domain attributes that short-circuit the audit

| Attribute | Effect |
|---|---|
| `VPCOptions` present | VPC domain. Skip Step 2. FGAC downgrades to CONFIG_GAP. Endpoint is private DNS. |
| `VPCOptions` absent | Public endpoint. Steps 2-3 at full severity. Endpoint is public DNS. |
| `EngineVersion: Elasticsearch_X.Y` | Legacy fork. Note as CONFIG_GAP (Step 4g). |
| `Processing: true` | Blue/green in flight. `update-domain-config` queues silently (see below). |
| `CustomEndpointEnabled: true` | Clients use custom DNS/cert, not describe endpoint. Cert expiry invisible in describe output. |

**Default-VPC trap:** a domain in the default VPC with public subnets is
effectively internet-facing despite having `VPCOptions` — the default VPC has
an internet gateway and public subnets by default. Check whether subnets have a
route to `0.0.0.0/0` via IGW. Treat default-VPC domains with PUBLIC_ACCESS
severity unless route table confirms no IGW path.

### aws/es CloudTrail opacity

The `aws/es` AWS-OWNED key is distinct from AWS-managed CMKs like `aws/s3`.
The OpenSearch service calls `kms:Decrypt` on its **own** service principal —
the customer sees **zero** `kms:Decrypt` events in CloudTrail for data access.
Contrast with S3's `aws/s3` AWS-managed key, where Decrypt events DO appear in
the customer's CloudTrail. A customer-managed CMK provides full CloudTrail
visibility, customer-controlled rotation, and a customer-authored key policy.
This is why `aws/es` is a CONFIG_GAP finding even when `Enabled: true` — the
data is encrypted but the customer has no audit trail for **when** it was
accessed by the service.

### describe-domain-access-policy is a separate API call

Unlike S3 (`get-bucket-policy` returns inline) or RDS, OpenSearch's resource
policy is **not** embedded in `describe-domain` / `describe-domain-config`
output. It requires a separate `describe-domain-access-policy` call. Auditors
and CI/CD scripts that use only `describe-domain-config` silently skip the
entire PUBLIC_ACCESS check (Step 2). A domain with **no resource policy
attached** returns empty `Policy` document — this is OK (account-level IAM is
the gate), NOT an error. Many automation scripts treat empty `Policy` as a
fetch failure and silently skip the access-policy check.

### update-domain-config silently queues behind in-progress blue/green

If a blue/green deployment is already running (`Processing: true`), a new
`update-domain-config` call returns HTTP 200 immediately but **does not
execute** — it queues silently behind the in-flight deployment. The operator
believes the change applied when it has not. Always check
`DomainStatus.Processing` before recommending any update. There is no API to
list queued updates — they are invisible until they execute (or are overwritten
by a newer call, which discards the queued one).

**Blue/green shard stall.** When shard count exceeds ~1000 per data node (the
default soft limit), the shard-relocation phase stalls — HTTP 200 but domain
hangs in "Processing" for hours, invisible in describe output. Recommend
pre-flight `_cat/shards` (data-plane call) for large domains.

### FGAC disablement is destructive and non-reversible

Disabling FGAC wipes the entire Security plugin state: all roles, role
mappings, action groups, and the internal user database. Re-enabling creates a
fresh state — all per-index controls must be rebuilt. You cannot "test" FGAC
by toggling it. The Security plugin REST API path also depends on engine
version: `_opendistro/_security/api/` for Elasticsearch ≤7.9 vs
`_plugins/_security/api/` for OpenSearch 1.1+. Wrong path returns 404.

### Cross-cluster search / replication security inversion

**CCS does not propagate FGAC.** When domain A registers domain B as a remote
(`cluster.remote.<alias>.seeds`), queries from A to B run as A's **connection
identity**, not the end-user's. FGAC role mappings, document-level security,
and field masking on B are NOT enforced for CCS queries. A "sanitized" local
domain querying a hardened remote inherits the remote's data without the
remote's per-index enforcement. Flag any CCS wiring as CONFIG_GAP.

**CCR inverts the risk.** The follower needs write permissions on the leader
(`indices:admin/index_template/create`, `indices:data/write/index`), expanding
the leader's write surface. Flag CONFIG_GAP if follower's role ARN is not in
the access policy.

## Anti-Patterns — NEVER

- **NEVER recommend "enable encryption-at-rest" or "enable NTN" as an in-place
  fix.** Both are **immutable** post-creation. Only remediation is domain
  recreation with a reindex. Confusing OpenSearch's immutable encryption with
  services that allow toggling (S3, EBS) is a common auditor mistake.
- **NEVER classify a VPC-backed domain as PUBLIC_ACCESS** regardless of access
  policy. VPC endpoints are not internet-reachable; SG/route table is the
  network boundary. (Wildcard principal is still NO_FGAC/CONFIG_GAP.)
- **NEVER treat `aws:SourceIp` (real CIDR) as a STRONG condition** for a public
  OpenSearch domain. VPN/NAT/proxy bypass. Only `aws:SourceArn`/`aws:SourceAccount`.
- **NEVER flag `Enabled: true` + `aws/es` as NO_ENCRYPTION.** Data IS encrypted;
  gap is customer control (no CloudTrail, rotation, key policy) = CONFIG_GAP.
- **NEVER assume FGAC is on because the access policy is restrictive.** FGAC is
  independent; always check `AdvancedSecurityOptions.Enabled` separately.
- **NEVER enable FGAC without first verifying NTN + HTTPS enforcement.** FGAC
  requires NTN, NTN requires HTTPS. Returns `ValidationException` otherwise.
- **NEVER recommend `DedicatedMasterCount` < 3 for HA.** Three across 3 AZs is
  minimum quorum. Count 1 = SPOF; count 2 = no quorum.
- **NEVER classify `t2/t3.small.search` as adequate for dedicated masters** on
  production domains. Below m5.large.search+ recommendation. Burstable masters
  silently drop cluster-state API calls under CPU-credit exhaustion.
- **NEVER state master-node resize requires domain recreation.** Master
  type/count changes ARE mutable via `update-domain-config` (blue/green). Only
  at-rest encryption and NTN are immutable.
- **NEVER assume CCS propagates FGAC.** CCS authenticates as the connection
  principal, bypassing remote per-index roles/DLS/masking. Flag as CONFIG_GAP.
- **NEVER assume a default-VPC domain is private.** Default VPC has IGW +
  public subnets. Check route tables before classifying as VPC-protected.
- **NEVER conflate provisioned OpenSearch with Serverless.** Serverless uses
  `aoss:API*`, always encrypted, OCU capacity. This skill is provisioned only.

## Pre-flight safety (before remediation CLI)

1. **MANDATORY confirmation gate** for every state-changing operation — emit
   CONFIRM prompt and halt. Applies to ALL updates without exception.
2. **Back up the access policy** before any change — OpenSearch access policies
   are NOT versioned (no version ID, no rollback, unlike IAM policies which have
   version identifiers):
   `aws opensearch describe-domain-access-policy --domain-name <name> --output json > /tmp/<name>-policy-backup-$(date +%s).json`
3. **Snapshot before encryption/NTN migration** — domain recreation without a
   snapshot loses all data. Manual snapshot to registered S3 repo required.
4. **Blue/green cost spike** — provisions parallel fleet (cost briefly doubles).
   Surface in CONFIRM gate.
5. **Verify caller IAM** — read-only auditor roles lack
   `opensearch:UpdateDomainConfig`; remediation fails with
   `AccessDeniedException`.
6. **NEVER disable FGAC as remediation** — wipes all roles/mappings/users.

## Recent AWS features (2024-2026)

- **OpenSearch Serverless GA (2024-2025):** OpenSearch Serverless provides auto-scaling search and analytics without cluster management. Auditors should note that Serverless collections have a different audit surface than provisioned domains — verify encryption, VPC access, and data-access policies at the collection level.
- **Security Analytics (2024):** OpenSearch Security Analytics provides threat detection rules and alerting on log data. Auditors should verify that security analytics detectors are configured for compliance-relevant log types (CloudTrail, VPC Flow Logs).
- **Fine-grained access control improvements (2024):** Enhanced FGAC with roles-based access control. Auditors should verify that the master user is not a shared account and that backend roles are scoped appropriately.
- **SAML authentication enhancements (2024-2025):** Improved SAML integration for OpenSearch Dashboards. Auditors should verify that SAML provider metadata is current and that IdP-initiated SSO is configured correctly.

## Domain

AWS CloudOps / OpenSearch Analytics Security & Compliance.
