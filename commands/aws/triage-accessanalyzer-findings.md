---
description: Triage IAM Access Analyzer findings (external access + unused access) into risk verdicts with remediation — classifies each finding as EXTERNAL_ACCESS, UNUSED_ACCESS, EXPECTED, or SAFE.
nl_triggers:
  - "access analyzer finding"
  - "triage access analyzer"
  - "external access finding"
  - "unused access finding"
  - "unused iam role"
  - "unused access key"
  - "isPublic finding"
  - "zone of trust"
  - "cross-account resource policy"
  - "archive rule suppression"
  - "kms key policy external"
  - "s3 bucket policy cross account"
  - "sqs queue public access"
  - "iam role trust external"
  - "service principal finding"
  - "expected external access"
routes_to: accessanalyzer-finding-triage
---

# /aws:triage-accessanalyzer-findings

Activate the `accessanalyzer-finding-triage` skill and triage one or more IAM
Access Analyzer findings into risk verdicts with remediation.

## What it does

Reads an IAM Access Analyzer finding (external-access or unused-access) and
applies the ordered classification logic:

1. Validate input and route by finding type (ExternalAccess vs Unused*).
2. **External access path:** check finding status, evaluate condition strength
   (cryptographic vs forgeable vs absent), classify principal type (public vs
   specific external vs service principal), apply resource-type severity
   matrix, check expected service integrations.
3. **Unused access path:** classify by finding type risk ranking (access key
   > password > role > permission > SCP), check expected-unused patterns
   (service-linked roles, break-glass roles).

Emits a deterministic VERDICT per finding:

```text
FINDING: <finding-id>
RESOURCE: <resource-arn>
RESOURCE_TYPE: <AWS::S3::Bucket | AWS::KMS::Key | ...>
FINDING_TYPE: ExternalAccess | UnusedIAMRole | ...
VERDICT: EXTERNAL_ACCESS | UNUSED_ACCESS | EXPECTED | SAFE
RISK: CRITICAL | HIGH | MODERATE | LOW
REASON: <1-2 sentences citing the finding detail and classification rule>
REMEDIATION: <specific action, or "None required" if expected/safe>
```

## When to invoke

Paste an Access Analyzer finding and ask any of:

- "triage this Access Analyzer finding"
- "is this external access finding a real risk?"
- "should I archive this finding?"
- "what's the risk level of this unused role?"
- "is this service principal finding expected?"
- "is this cross-account access expected or a security risk?"

A bare finding JSON + any triage verb also routes here.

## Inputs

- An IAM Access Analyzer finding (JSON or structured text), pasted inline or
  referenced by file path. Include the finding type, resource type, principal,
  condition, actions, isPublic, and status.
- Optional: context about the finding (e.g., "this is a CI/CD account" or
  "this is a break-glass role") for more accurate EXPECTED classification.
- Optional: the analyzer type (ACCOUNT vs ORGANIZATION) for zone-of-trust
  context.

## Outputs

- One VERDICT block per finding.
- Specific remediation: resource-policy restriction commands, archive-rule
  creation patterns, credential deactivation steps, and pre-flight safety
  backup commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the Phase 2
  Audit specialist for Access Analyzer findings).
- `/aws:audit-iam-least-privilege` for identity-based policy analysis after
  remediating unused-access findings.
- `/aws:audit-s3-public-access` for S3 BPA/ACL-level analysis complementing S3
  external-access finding triage.
