---
description: Audit an Athena workgroup for query-result encryption (SSE-S3/SSE-KMS), data-scan limit (BytesScannedCutoffPerQuery), enforcement posture (EnforceWorkGroupConfiguration), query-history retention via CloudTrail data events, and named-query IAM exposure.
nl_triggers:
  - "audit this Athena workgroup"
  - "check Athena workgroup encryption"
  - "is Athena workgroup enforced"
  - "Athena data scan limit"
  - "BytesScannedCutoffPerQuery"
  - "EnforceWorkGroupConfiguration false"
  - "primary workgroup defaults"
  - "Athena query history retention"
  - "named query IAM"
  - "Athena cost blast radius"
  - "Athena result encryption"
  - "Athena workgroup config"
  - "SSE-KMS Athena"
  - "Athena workgroup security"
routes_to: athena-workgroup-auditor
---

# /aws:audit-athena-workgroup

Activate the `athena-workgroup-auditor` skill and audit one or more Athena
workgroup configurations (Configuration block + workgroup metadata +
optional named queries + CloudTrail context) for security, cost, and
compliance exposure.

## What it does

Reads an Athena workgroup Configuration block and applies the ordered
classification logic:

1. Pre-flight gate — `primary` workgroup (undeletable, weak defaults),
   engine type (SQL vs AthenaSpark), State (DISABLED workgroups cannot
   produce live findings).
2. Enforcement gate — `EnforceWorkGroupConfiguration` is the keystone.
   When false, ResultConfiguration (encryption, OutputLocation) is
   advisory; only the DSL remains binding (no per-query override API
   exists).
3. Encryption evaluation — absent EncryptionConfiguration is NO_ENCRYPTION
   (plaintext result objects in S3); SSE_S3 is acceptable; SSE_KMS with a
   CMK is preferred for compliance workloads.
4. Data-scan limit — absent BytesScannedCutoffPerQuery is NO_LIMITS
   (unbounded cost + cross-workgroup quota impact). Spark workgroups skip
   this step (DSL does not apply to Spark sessions).
5. Query history retention — Athena's GetQueryExecution API has a fixed
   45-day window; no CloudTrail Athena data events = CONFIG_GAP (no
   long-term audit trail).
6. Named-query IAM — `Principal: "*"` or cross-account grants on
   `athena:GetNamedQuery` / `StartNamedQuery` = CONFIG_GAP (SQL
   exfiltration surface; named queries are plaintext).
7. Aggregation — worst finding wins (NO_ENCRYPTION > NO_LIMITS >
   CONFIG_GAP > OK).

Emits a deterministic VERDICT per workgroup:

```text
WORKGROUP: <name>
VERDICT: NO_ENCRYPTION | NO_LIMITS | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an Athena workgroup Configuration block and ask any of:

- "audit this Athena workgroup"
- "is my Athena result location encrypted?"
- "is the workgroup enforced?"
- "do we have a data scan limit?"
- "what's the blast radius of this Athena workgroup?"
- "is query history retained past 45 days?"
- "are named queries leaking SQL?"

A bare workgroup name + any audit verb ("audit primary workgroup",
"check etl workgroup config") also routes here via the orchestrator.

## Inputs

- An Athena workgroup Configuration block (JSON), pasted inline or
  referenced by file path. The block returned by
  `aws athena get-work-group --work-group <name> --output json` is the
  canonical shape.
- Workgroup metadata: Name, State, Description. The `Name` drives the
  `primary` short-circuit; `State: DISABLED` skips live-blast findings.
- For the query-history dimension: whether any CloudTrail trail in the
  workgroup's region has Athena data events enabled
  (`aws cloudtrail get-event-selectors --trail-name <trail>`).
- For the named-query dimension: a list of named queries
  (`aws athena list-named-queries --work-group <name>` →
  `aws athena get-named-query --named-query-id <id>`) plus the IAM grants
  on the workgroup ARN.

## Outputs

- One VERDICT block per workgroup (multiple findings aggregate to the
  highest-priority category).
- Enumerated FINDINGS list with per-finding category and step citation.
- Specific remediation: configure SSE-KMS, set a DSL, flip enforcement
  on, enable CloudTrail data events, scope named-query IAM, or lock down
  the `primary` workgroup.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Athena analytics security & cost control).
- `/aws:audit-kms-key-policy` when the Athena workgroup uses SSE-KMS and
  you want to audit the KMS key policy that backs it (the key policy
  must permit `athena.<region>.amazonaws.com` for `GenerateDataKey` and
  `Decrypt`).
- `/aws:audit-cloudtrail-org-trail` to verify the trail capturing Athena
  events is itself healthy (multi-region, log-file validation, retention).
