---
description: Audit an AWS CodeBuild project for privileged mode (Docker-in-Docker), plaintext secrets in environment variables, unencrypted S3 logs and artifacts, over-permissive service-role blast radius (PassRole, admin wildcard), VPC network exposure, and public build-status badge leakage.
nl_triggers:
  - "audit this CodeBuild project"
  - "check CodeBuild privileged mode"
  - "CodeBuild secret in env var"
  - "CodeBuild service role too permissive"
  - "CodeBuild S3 logs unencrypted"
  - "CodeBuild build badge public"
  - "CodeBuild VPC config missing"
  - "CodeBuild IAM blast radius"
  - "Docker-in-Docker CodeBuild"
  - "privilegedMode CodeBuild"
  - "hardening CodeBuild"
  - "CodeBuild security audit"
routes_to: codebuild-project-auditor
---

# /aws:audit-codebuild-project

Activate the `codebuild-project-auditor` skill and audit one or more
CodeBuild project configurations (project config + service-role policy)
for security exposure.

## What it does

Reads a CodeBuild project configuration (the `batch-get-projects` output)
plus the service-role identity-based and trust policies, and applies the
ordered classification logic:

1. Pre-flight project metadata gate — short-circuit `PUBLIC_READ`
   visibility, custom-image posture, AWS-managed image baseline.
2. Privileged mode — `privilegedMode: true` with no Docker usage in the
   inline buildspec is PRIVILEGED (host-equivalent container privilege).
3. Plaintext secret leak — `environmentVariables[type=PLAINTEXT]` with a
   secret-shaped key (PASSWORD, TOKEN, KEY) is SECRET_LEAK.
4. Encryption posture — `s3LogsConfig.encryptionDisabled: true` OR
   `artifacts.encryptionDisabled: true` OR missing `kmsKeyArn` is
   NO_ENCRYPTION.
5. Service-role blast radius — `Action: "*"` on `Resource: "*"`,
   `iam:PassRole` on `"*"`, unscoped `codebuild.amazonaws.com` trust
   policy is OVERPERMISSIVE_ROLE.
6. VPC config — missing `vpcConfig` with cross-VPC resources or public
   subnets is CONFIG_GAP.
7. Badge — `badgeEnabled: true` exposes a public build-status URL.
8. Aggregation — worst finding wins
   (PRIVILEGED > SECRET_LEAK > NO_ENCRYPTION > OVERPERMISSIVE_ROLE >
   CONFIG_GAP > OK).

Emits a deterministic VERDICT per project:

```text
PROJECT: <name>
VERDICT: PRIVILEGED | SECRET_LEAK | NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [PRIVILEGED] <finding description (Step Na)>
  - [CONFIG_GAP] <finding description (Step Nb)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a CodeBuild project config and ask any of:

- "audit this CodeBuild project"
- "is my CodeBuild container privileged?"
- "are there secrets in CodeBuild env vars?"
- "is my CodeBuild service role too permissive?"
- "is the CodeBuild badge public?"
- "what's the blast radius of this CodeBuild role?"

A bare project name or ARN plus any audit verb ("audit this build",
"check CodeBuild config") also routes here via the orchestrator.

## Inputs

- A CodeBuild project configuration (JSON), pasted inline or referenced
  by file path. Required fields: `name`, `source`, `environment`,
  `serviceRole`, `logsConfig`, `artifacts`, `badgeEnabled`, `vpcConfig`.
- The service-role identity-based policy (inline + attached managed
  policies) for Step 4. If omitted, the OVERPERMISSIVE_ROLE dimension is
  noted as "not evaluated" — never guessed.
- The service-role trust policy (`assumeRolePolicyDocument`) for Step 4c.
  Recommended but not required; if omitted, the confused-deputy check is
  noted as "post-check required".

## Outputs

- One VERDICT block per project (multiple findings aggregate to the
  worst severity per the strict priority order).
- Enumerated FINDINGS list with per-finding verdict tag and step
  citation.
- Specific remediation: disable privilegedMode, move secrets to Secrets
  Manager, scope the service role, scope the trust policy, enable SSE-KMS
  logs, disable the badge, move to private VPC subnets.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for CodeBuild / Developer Tools security).
- `/aws:audit-iam-least-privilege` for deeper IAM policy analysis when
  the CodeBuild service role has many statements to enumerate.
- `/aws:audit-kms-key-policy` when the CodeBuild project uses a
  customer-managed KMS key and the key policy itself needs review.
