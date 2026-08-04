---
description: Audit an ECR private repository for public access via repositoryPolicy, scan-on-push gaps, lifecycle-policy absence, tag-immutability gaps, and unscanned images.
nl_triggers:
  - "audit this ECR repository"
  - "check ECR repository policy"
  - "is my ECR repo public"
  - "ECR scanOnPush enabled"
  - "ECR lifecycle policy"
  - "unscanned container images"
  - "tag immutability check"
  - "ECR cross-account access"
  - "container image vulnerability scan"
  - "ECR Principal star"
  - "ECR public pull"
  - "hardening ECR repository"
  - "container supply chain security"
routes_to: ecr-repository-auditor
---

# /aws:audit-ecr-repository

Activate the `ecr-repository-auditor` skill and audit one or more ECR private
repositories for security exposure and supply-chain posture.

## What it does

Reads an ECR repository configuration bundle (repositoryPolicy +
imageScanningConfiguration + imageTagMutability + lifecyclePolicyText +
image metadata) and applies the ordered classification logic:

1. Pre-flight metadata gate — short-circuit empty repositoryPolicy
   (IAM-only, the secure default), classify encryption type.
2. PUBLIC — repositoryPolicy with `Principal: "*"` or cross-account
   principal granting pull/push actions without a STRONG condition.
   `aws:SourceVpce`/`aws:SourceAccount` downgrades to CONFIG_GAP.
3. NO_SCAN — `scanOnPush: false` AND images with `imageScanStatus` null
   or incomplete.
4. NO_LIFECYCLE — no `lifecyclePolicyText` present.
5. CONFIG_GAP — `imageTagMutability: MUTABLE`, cross-account metadata-only,
   or condition-restricted wildcard principal.
6. Aggregation — worst finding wins (PUBLIC > NO_SCAN > NO_LIFECYCLE >
   CONFIG_GAP > OK).

Emits a deterministic VERDICT per repository:

```text
REPO: <registry-id>.dkr.ecr.<region>.amazonaws.com/<repo-name>
VERDICT: PUBLIC | NO_SCAN | NO_LIFECYCLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [PUBLIC] <finding description (Step 1a)>
  - [NO_SCAN] <finding description (Step 2)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an ECR repository configuration and ask any of:

- "audit this ECR repository"
- "is my ECR repo publicly accessible?"
- "check ECR repository policy"
- "is scan-on-push enabled?"
- "does this repo have a lifecycle policy?"
- "are there unscanned images?"
- "is tag immutability set?"

A bare repository ARN or name + any audit verb ("audit this repo",
"check ECR config") also routes here via the orchestrator.

## Inputs

- An ECR repository policy document (JSON), pasted inline or referenced by
  file path.
- Repository metadata: `imageScanningConfiguration.scanOnPush`,
  `imageTagMutability`, `lifecyclePolicyText` (present/absent),
  `encryptionConfiguration.encryptionType`.
- Image metadata: per-image `imageScanStatus` (null/PENDING/COMPLETE).
- For multi-repo sweeps: provide pagination handling via `--next-token`.

## Outputs

- One VERDICT block per repository (multiple findings aggregate to the
  worst severity).
- Enumerated FINDINGS list with per-finding verdict and step citation.
- Specific remediation: tighten repositoryPolicy, enable scanOnPush,
  apply lifecycle policy, set tag immutability, run image scans.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for ECR/container supply-chain security).
- `/aws:audit-kms-key-policy` for KMS key policy analysis (relevant when
  ECR uses KMS encryption).
- `/aws:audit-iam-least-privilege` for IAM policy analysis of roles that
  may have ECR permissions in their identity-based policies.
