---
description: Audit a CodePipeline pipeline for artifact-store encryption gaps (no KMS CMK), cross-account deploy roles, disabled stage transitions, deprecated source credentials (GitHub v1), and missing manual approval gates.
nl_triggers:
  - "audit this codepipeline"
  - "check pipeline artifact store encryption"
  - "cross-account deploy role in pipeline"
  - "disabled stage transition"
  - "github v1 source deprecated"
  - "missing manual approval gate"
  - "pipeline security audit"
  - "over-permissive pipeline role"
  - "codestar connection check"
  - "is my pipeline encrypted"
  - "pipeline approval gate missing"
  - "codepipeline source credentials"
  - "artifact bucket kms key"
  - "pipeline stage frozen"
routes_to: codepipeline-pipeline-auditor
---

# /aws:audit-codepipeline-pipeline

Activate the `codepipeline-pipeline-auditor` skill and audit one or more
CodePipeline pipeline definitions for security and operational exposure.

## What it does

Reads a CodePipeline pipeline definition JSON (from `get-pipeline`),
optionally paired with `get-pipeline-state` output for transition status,
and applies the ordered classification logic:

1. Artifact store encryption — check for `encryptionKey` (CMK) presence;
   absent key means artifacts are UNENCRYPTED at rest.
2. Cross-account / over-permissive roles — extract action
   `configuration.RoleArn` account IDs; any account differing from the
   pipeline owner is OVERPERMISSIVE_ROLE.
3. Stage transition state — check `inboundTransitionState.enabled`; a
   disabled transition is DISABLED_STAGE (operational freeze).
4. Source action credentials — ThirdParty/GitHub (v1 OAuth) is deprecated
   and a credential-exposure vector; AWS/CodeStarConnection is secure.
5. Manual approval gate — production pipelines without ManualApproval
   or with missing NotificationArn are CONFIG_GAP.
6. Aggregation — worst finding wins (NO_ENCRYPTION > OVERPERMISSIVE_ROLE
   > DISABLED_STAGE > CONFIG_GAP > OK).

Emits a deterministic VERDICT per pipeline:

```text
PIPELINE: <name>
VERDICT: NO_ENCRYPTION | OVERPERMISSIVE_ROLE | DISABLED_STAGE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a CodePipeline pipeline definition and ask any of:

- "audit this codepipeline"
- "is my pipeline artifact store encrypted?"
- "check for disabled stage transitions"
- "is this pipeline using deprecated GitHub source?"
- "does this pipeline have an approval gate?"
- "what roles does this pipeline use?"

A bare pipeline name or ARN + any audit verb ("audit this pipeline",
"check pipeline security") also routes here via the orchestrator.

## Inputs

- A CodePipeline pipeline definition JSON (from `aws codepipeline
  get-pipeline --name <name> --output json`), pasted inline or referenced
  by file path.
- Pipeline state output (from `aws codepipeline get-pipeline-state --name
  <name>`) for disabled-stage-transition detection. Without this, the
  auditor cannot definitively classify disabled transitions.
- Artifact bucket SSE metadata (optional but recommended — confirms
  whether the bucket has SSE-KMS, SSE-S3, or no encryption).

## Outputs

- One VERDICT block per pipeline (multiple findings aggregate to the
  worst severity category).
- Enumerated FINDINGS list with per-finding category and step citation.
- Specific remediation: add CMK, scope roles, migrate to CodeStar
  Connection, add approval gate, re-enable transitions.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for CodePipeline CI/CD security).
- `/aws:audit-kms-key-policy` for auditing the KMS key used by the
  pipeline's artifact store.
- `/aws:audit-iam-least-privilege` for analyzing the IAM policies of
  roles referenced in pipeline action configurations.
