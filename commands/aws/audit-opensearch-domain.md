---
description: Audit an Amazon OpenSearch Service domain for encryption-at-rest, node-to-node encryption, fine-grained access control, public access, dedicated master node sizing, and slow log publishing.
nl_triggers:
  - "audit this OpenSearch domain"
  - "check OpenSearch encryption"
  - "OpenSearch node-to-node encryption off"
  - "is my OpenSearch domain public"
  - "OpenSearch FGAC disabled"
  - "is Advanced Security enabled"
  - "OpenSearch Principal star"
  - "es:ESHttp* public"
  - "OpenSearch dedicated master too small"
  - "t3.small.search dedicated master"
  - "OpenSearch slow logs not published"
  - "harden OpenSearch domain"
  - "OpenSearch compliance audit"
  - "Amazon OpenSearch Service audit"
  - "review OpenSearch configuration"
routes_to: opensearch-domain-auditor
---

# /aws:audit-opensearch-domain

Activate the `opensearch-domain-auditor` skill and audit one or more Amazon
OpenSearch Service (provisioned, not Serverless) domains for security exposure
and configuration gaps.

## What it does

Reads an OpenSearch domain configuration (describe-domain-config +
describe-domain-access-policy) and applies the ordered classification logic:

1. Encryption-at-rest — `EncryptionAtRestOptions.Enabled: false` is
   NO_ENCRYPTION (CRITICAL; immutable post-creation — domain recreation is
   the only remediation). AWS-managed `aws/es` key is a CONFIG_GAP finding
   (encrypted but operationally opaque).
2. Public access policy — `Principal: "*"` + `es:ESHttp*` / `es:*` + no
   STRONG condition is PUBLIC_ACCESS (any AWS account holder can read/write
   every document).
3. Fine-grained access control — `AdvancedSecurityOptions.Enabled: false`
   on internet-facing domains is NO_FGAC (no per-index/per-role enforcement
   layer). On VPC domains it downgrades to CONFIG_GAP.
4. Configuration gaps — node-to-node encryption off (immutable),
   `t2/t3.small.search` dedicated masters (below AWS recommendation),
   missing slow log publishing, HTTPS enforcement off, AWS-managed KMS key,
   `DedicatedMasterCount < 3`, single-AZ multi-node clusters.
5. Aggregation — worst finding wins. Precedence:
   `NO_ENCRYPTION > PUBLIC_ACCESS > NO_FGAC > CONFIG_GAP > OK`.

Emits a deterministic VERDICT per domain:

```text
DOMAIN: <domain-name>
VERDICT: NO_ENCRYPTION | PUBLIC_ACCESS | NO_FGAC | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [PUBLIC_ACCESS] <finding description (Step 2a)>
  - [CONFIG_GAP] <finding description (Step 4a)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an OpenSearch domain configuration and ask any of:

- "audit this OpenSearch domain"
- "is my OpenSearch domain public?"
- "check OpenSearch encryption at rest"
- "is node-to-node encryption on?"
- "is Advanced Security / FGAC enabled?"
- "are slow logs being published?"
- "is my dedicated master sized correctly?"

A bare domain name or ARN + any audit verb ("audit this domain",
"check OpenSearch config") also routes here via the orchestrator.

## Inputs

- Domain configuration: EngineVersion, ClusterConfig (DedicatedMaster*,
  InstanceType/Count, ZoneAwarenessEnabled), EncryptionAtRestOptions,
  NodeToNodeEncryptionOptions, DomainEndpointOptions.EnforceHTTPS,
  AdvancedSecurityOptions, VPCOptions (present = VPC domain, absent =
  internet-facing), LogPublishingOptions.
- Access policy JSON (resource-based policy attached to the domain).
- For live-account audits: the skill references describe-domain,
  describe-domain-config, describe-domain-access-policy, and
  list-domain-names.

## Outputs

- One VERDICT block per domain (multiple findings aggregate to the worst
  severity per the precedence order).
- Enumerated FINDINGS list with per-finding verdict tag and step citation.
- Specific remediation: domain recreation for immutable gaps (at-rest
  encryption, NTN), in-place updates for mutable gaps (FGAC enablement,
  slow log publishing, dedicated master sizing), assume-breach workflow for
  PUBLIC_ACCESS (audit CloudTrail for `es:ESHttp*` events during exposure).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for OpenSearch Analytics security).
- `/aws:audit-kms-key-policy` for auditing the customer-managed CMK policy
  when the domain uses `KmsKeyId` for at-rest encryption.
