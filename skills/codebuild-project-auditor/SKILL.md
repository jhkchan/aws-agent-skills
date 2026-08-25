---
name: codebuild-project-auditor
description: Audits AWS CodeBuild projects for privileged mode (Docker-in-Docker host kernel access), plaintext secrets in environment variables, unencrypted S3 logs and build artifacts, over-permissive service-role blast radius (PassRole, admin wildcard), VPC/network exposure, and public build-status badge leakage. Emits a deterministic verdict (PRIVILEGED | SECRET_LEAK | NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK) per project with enumerated findings and specific remediation. Use when reviewing CodeBuild projects, checking for privileged build containers, validating secret injection posture, auditing build-role IAM scope, hardening build-network isolation, or verifying encryption of logs and artifacts before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline project-config classification. Live-account audits use aws codebuild batch-get-projects, aws iam list-attached-role-policies, aws iam list-role-policies, and aws iam get-role-policy (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  verdict_shape: PRIVILEGED | SECRET_LEAK | NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
  when_to_use: Reviewing a CodeBuild project before production deployment, checking for privileged build containers, auditing secret-handling posture, validating that S3 logs and build artifacts are SSE-KMS encrypted, scoping down the CodeBuild service role, hardening VPC isolation for build network egress, or auditing the public build-status badge exposure across an account.
  activation_triggers: audit this CodeBuild project, is my CodeBuild container privileged, check CodeBuild for secrets in env vars, CodeBuild S3 logs unencrypted, CodeBuild service role too permissive, CodeBuild build badge public, harden my CodeBuild project, CodeBuild VPC config missing, CodeBuild IAM blast radius
  invocation_schema: 'Input: either (a) a CodeBuild project configuration JSON document (describe-project output) optionally paired with the service-role identity-based policy, OR (b) a project name/ARN for live-account audit. Output: deterministic PROJECT/VERDICT/REASON/FINDINGS/REMEDIATION block per project, where VERDICT is in {PRIVILEGED, SECRET_LEAK, NO_ENCRYPTION, OVERPERMISSIVE_ROLE, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CodeBuild, build project, privileged mode, Docker-in-Docker, DinD, secret leak, environment variables, Secrets Manager, SSM Parameter Store, S3 logs encryption, SSE-KMS, build artifacts, service role, IAM blast radius, PassRole, admin wildcard, VPC config, build badge, badge enabled, public leak, build hardening, container security
  tags: codebuild, devtools, security, build-pipeline, privileged-mode, secrets, iam, encryption, vpc, audit
---

# CodeBuild Project Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
six ordered dimensions, and the priority is strict —
`PRIVILEGED > SECRET_LEAK > NO_ENCRYPTION > OVERPERMISSIVE_ROLE > CONFIG_GAP > OK`.

The four-facts deep-dive (privilegedMode host access, plaintext env vars, encryptionDisabled KMS opt-out, service-role escalation launchpad): [Advanced patterns](references/advanced-patterns.md).

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `environment.privilegedMode: true` on a non-Docker build | **PRIVILEGED** | Step 1 |
| `environment.privilegedMode: true` on a Docker build with no fileSystemLocations and noSYS_ADMIN cap | **PRIVILEGED** | Step 1 |
| Plaintext secret-pattern value in `environment.environmentVariables` (type PLAINTEXT/omitted) | **SECRET_LEAK** | Step 2 |
| `s3LogsConfig.encryptionDisabled: true` | **NO_ENCRYPTION** | Step 3a |
| `artifacts.encryptionDisabled: true` | **NO_ENCRYPTION** | Step 3b |
| `s3LogsConfig.status: ENABLED` and no `kmsKeyArn` and no SSE-S3-only justification | **NO_ENCRYPTION** | Step 3c |
| Service-role statement with `Action: "*"` on `Resource: "*"` | **OVERPERMISSIVE_ROLE** | Step 4a |
| Service-role grants `iam:PassRole` / `sts:AssumeRole` on `"*"` | **OVERPERMISSIVE_ROLE** | Step 4b |
| Service-role trust policy not scoped to project ARN via `aws:SourceArn`/`sts:ExternalId` | **OVERPERMISSIVE_ROLE** (sub-finding) | Step 4c |
| No `vpcConfig` and the project fetches secrets/artifacts cross-VPC | **CONFIG_GAP** | Step 5a |
| `badgeEnabled: true` | **CONFIG_GAP** | Step 6 |
| `logsConfig.cloudWatchLogs.status: DISABLED` and `s3LogsConfig.status: DISABLED` | **CONFIG_GAP** (forensics gap) | Step 7a |
| All dimensions pass | **OK** | Step 8 |

See the ordered steps below for edge cases. Deep CodeBuild internals
(build-host isolation, secrets-resolution pipeline, fleet multi-tenancy)
are in the [Deep reference](#deep-reference-codebuild-internals) section
at the end.

## Pre-flight: project metadata gate (run before classification)

Before classifying, sanity-check the project. Several attributes
**short-circuit** the audit — misclassifying them produces false positives
that erode trust.

**Multi-project / account-wide sweep note (pagination):** when auditing
every project in an account, `aws codebuild list-projects` returns at most
100 per page. Use `--next-token` from the prior `nextToken` to page
through. For each project name, also page the service-role policy
enumeration: `aws iam list-role-policies`, `aws iam list-attached-role-policies`,
and `aws iam get-policy-version` for each attached managed policy. Always
drain `nextToken` to completion — the long tail is where stale, exposed, or
forgotten projects live.

**Live-account pre-flight checks (skip if doing offline project-config
audit):**
1. Verify the caller's identity can run `codebuild:DeleteProject` /
   `UpdateProject` if remediation is intended — most read-only auditor
   roles CANNOT. Surface this BEFORE the operator approves the change.
2. Verify CloudTrail is logging CodeBuild **data events** for
   `StartBuild` / `StopBuild` / `BatchGetBuilds`. Management events are on
   by default, but build-batch and report data events must be explicitly
   enabled. Without them, build-source forensics have no signal.
3. Snapshot the current buildspec and project config BEFORE any edit —
   `batch-get-projects` is not versioned. There is no undo without a
   backup file.

| Attribute | Value | Effect on audit |
|---|---|---|
| `projectVisibility` | `PUBLIC_READ` | **Public project** — any AWS account can start builds. Treat as CRITICAL-level misconfiguration regardless of other dimensions. Output a separate `VISIBILITY_PUBLIC` finding and refuse to remediate inline; quarantine the project. |
| `environment.type` | `LINUX_CONTAINER` / `WINDOWS_SERVER_2019_CONTAINER` / `ARM_CONTAINER` | Standard container fleet. Proceed with audit. |
| `environment.image` | `aws/codebuild/standard:*` | **AWS-managed image.** Runs as non-root `codebuild-user` by default. Still audit privilegedMode and env vars. |
| `environment.image` | Custom (e.g. ECR ARN) | **Custom image.** Verify the image runs as non-root; if the Dockerfile ends with `USER root` or omits USER, the build runs as root inside the container (separate from privilegedMode). Note as INSECURE sub-finding. |
| `environment.computeType` | `BUILD_GENERAL1_LARGE` / `BUILD_GENERAL1_XLARGE` | Compute tier — operational, not security. |
| `source.type` | `GITHUB` / `BITBUCKET` / `CODECOMMIT` etc. | Source provider. If `GITHUB` with `webhook: true`, any push to the configured repo triggers a build — review whether PR builds run with the same elevated role. |
| `cache.type` | `S3` | S3 cache. Verify the cache bucket is in the same account and has BLOCK_PUBLIC_ACCESS on. |
| `cache.type` | `LOCAL` | Local cache (instance-only). No S3 exposure. |
| `encryptionKey` (top-level) | omitted | **AWS-managed SSE-KMS key** for CodeBuild artifacts. Acceptable defense-in-depth baseline. |
| `encryptionKey` (top-level) | Customer key ARN | Customer-managed SSE-KMS key. OK. |

**If the project config JSON is malformed** (invalid JSON, missing `source`
or `environment`), output:

```text
PROJECT: <name>
VERDICT: ERROR
REASON: Project config is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws codebuild batch-get-projects --names <name> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious CodeBuild behaviors that change classification

These behaviors are easy to misjudge without operational CodeBuild
experience. Each changes a verdict if ignored:

All 20 non-obvious behaviors (DinD requirement, PLAINTEXT type default, secretsManager array shape, SSE-S3 vs SSE-KMS, legacy cross-account artifacts, console trust-policy wildcards, iam:PassRole escalation, source-auth credential ARNs, ECR scan-on-push, inline vs source buildspec, EFS mounts, PUBLIC_READ, webhook status leaks, cache poisoning, Nitro isolation, un-versioned configs, imagePullCredentialsType, full-replace update gotcha): [Advanced patterns](references/advanced-patterns.md).

### Step 1: Privileged mode — Docker-in-Docker classification

If `environment.privilegedMode` is `true`:

- If `source.buildspec` (inline) contains no `docker build`, `docker
  push`, `docker run`, `docker-compose`, or `buildctl` usage → **PRIVILEGED**.
  The build has host-equivalent container privileges for no Docker reason.
- If `source.buildspec` is NOT set (buildspec comes from source repo)
  → **PRIVILEGED** with a NOTE: "Buildspec from source — fetch the
  branch's `buildspec.yml` to confirm Docker requirement:
  `aws codecommit get-file --repository-name <r> --commit-specifier <branch> --file-path buildspec.yml`
  (CodeCommit) or `gh api repos/<owner>/<repo>/contents/buildspec.yml?ref=<branch>`
  (GitHub). Treat privilegedMode as active host access until verified."
- If the inline buildspec explicitly runs Docker commands → NOT a
  PRIVILEGED finding. Privileged mode is the documented mechanism for
  DinD. Note in FINDINGS: "[OK] privilegedMode enabled for Docker-in-Docker
  build — expected." Also emit a Step 7e NOTE about ECR scan-on-push.
- If `environment.privilegedMode: true` AND `environment.image` is a
  Docker-in-Docker image (`docker:dind`, `jpetazzo/dind`) → NOT a
  PRIVILEGED finding. The image is purpose-built.

If `privilegedMode` is `false` or omitted → no PRIVILEGED dimension.

### Step 2: Plaintext secret leak classification

For each entry in `environment.environmentVariables`:

- If `type` is omitted or `PLAINTEXT`: the value is committed plaintext.
  Apply the **secret-pattern heuristics** to the value:
  - Key name matches: `(?i).*(password|passwd|pwd|secret|api[_-]?key|access[_-]?key|secret[_-]?key|private[_-]?key|token|client[_-]?secret|db[_-]?pass|creds?|auth).*$`
  - Value matches AWS key patterns: `AKIA[0-9A-Z]{16}` (access-key-id),
    `aws4_request` signature fragments, `-----BEGIN .* PRIVATE KEY-----`
  - Value matches high-entropy strings (>=32 chars, mixed case+digits) when
    the key name is secret-shaped
- If a plaintext entry matches any pattern → **SECRET_LEAK**.
- If `type: PARAMETER_STORE` or `SECRETS_MANAGER` → NOT plaintext. The
  entry stores a parameter/secret ARN reference; the value is fetched at
  build time. Do NOT flag.
- `environment.secretsManager[]` entries are ALWAYS reference-based. Do
  NOT flag.

**Subtle distinction:** a variable named `DATABASE_URL` with value
`postgres://user:pass@host:5432/db` is a SECRET_LEAK — the password is
embedded in the URL. Apply URL-pattern detection: `^[a-z]+://[^:]+:[^@]+@`.

### Step 3: Encryption posture — S3 logs and build artifacts

Apply in order; first hit wins for the dimension:

- **3a.** If `s3LogsConfig.status: ENABLED` and
  `s3LogsConfig.encryptionDisabled: true` → **NO_ENCRYPTION**. The logs
  bucket receives build logs without customer-managed SSE-KMS.
- **3b.** If `artifacts.encryptionDisabled: true` → **NO_ENCRYPTION**.
  Build output artifacts are written without SSE-KMS.
- **3c.** If `s3LogsConfig.status: ENABLED` and `s3LogsConfig.kmsKeyArn`
  is omitted/empty → **NO_ENCRYPTION**. The logs use SSE-S3 only (no
  customer-managed key). The field is the only way to opt into SSE-KMS;
  omitting it means default-only encryption.
- **3d.** If `s3LogsConfig.status: DISABLED` and
  `cloudWatchLogs.status: ENABLED` → no NO_ENCRYPTION dimension (CloudWatch
  logs are encrypted by default, server-side). Note: log-group KMS
  encryption is a separate dimension (Step 7b).
- If `s3LogsConfig.encryptionDisabled: false` AND `kmsKeyArn` set → OK
  for this dimension.

### Step 4: Service-role blast radius

Examine the service role's identity-based policy (inline + attached). If
no policy document is provided in input, output a NOTE: "service-role
policy not supplied — IAM dimension cannot be evaluated statically. Run
`aws iam list-role-policies --role-name <role>` and re-audit." Do NOT
guess a verdict for the missing dimension.

For each `Effect: Allow` statement in the role's identity-based policy:

- **4a.** `Action: "*"` AND `Resource: "*"` → **OVERPERMISSIVE_ROLE**
  (admin wildcard). Highest-severity role finding.
- **4b.** Any of `iam:PassRole`, `sts:AssumeRole`,
  `iam:CreatePolicy`, `iam:AttachRolePolicy`, `iam:PutRolePolicy`,
  `iam:UpdateAssumeRolePolicy` on `Resource: "*"` →
  **OVERPERMISSIVE_ROLE** (privilege-escalation vector).
- **4c.** Service-wildcard action (`s3:*`, `ec2:*`, `secretsmanager:*`,
  `kms:*`, `ssm:*`, `lambda:*`, `cloudformation:*`) on `Resource: "*"` →
  **OVERPERMISSIVE_ROLE** (service-level wildcard on all resources).
- **4d.** Trust policy (`assumeRolePolicyDocument`) Principal is
  `{"Service": "codebuild.amazonaws.com"}` with NO `Condition` block
  scoping `aws:SourceArn` or `aws:SourceAccount` to this project →
  **OVERPERMISSIVE_ROLE** sub-finding (confused-deputy vector). Any
  CodeBuild project in the account can assume this role. The remediation
  is adding `Condition: {StringEquals: {"aws:SourceArn": "<project-arn>"}}`.

If all role statements have named actions on specific ARNs AND the trust
policy is scoped → OK for this dimension.

### Step 5: VPC configuration — network exposure

- **5a.** No `vpcConfig` block AND the project fetches secrets / writes
  artifacts to cross-VPC resources → **CONFIG_GAP**. The build has direct
  internet egress (default network), which is an exfiltration path for
  any secret the build can read. If all source/artifact/secret resources
  are public-internet-hosted (e.g., public GitHub, public PyPI), no
  CONFIG_GAP — the build has nothing to exfiltrate to a private endpoint.
- **5b.** `vpcConfig` present AND `subnets` are all public subnets
  (route table includes `0.0.0.0/0` via IGW) → **CONFIG_GAP**. The build
  is "in a VPC" but still has direct internet egress — the VPC adds no
  isolation. Use private subnets + NAT gateway for true egress control.
- **5c.** `vpcConfig` present with private subnets and security groups
  that allow `0.0.0.0/0` egress → **CONFIG_GAP** (overly broad SG).
- **5d.** `vpcConfig` present with private subnets, restrictive SG, and
  no NAT (air-gapped) → OK.

If you cannot determine subnet type (offline audit with only project
config) AND `vpcConfig` is present, treat as OK for this dimension with a
NOTE: "subnet classification requires DescribeRouteTables; treat as
verified post-check."

### Step 6: Build badge — public status leakage

If `badgeEnabled: true`:

- The badge URL is `https://codebuild.<region>.amazonaws.com/badges/api/v1/project/<hash>/branch/<branch>/status.svg`
- This URL is **publicly accessible without authentication**. Anyone with
  the URL (or who guesses/enumerates it) can see the latest build status
  for the branch. The URL does NOT reveal the project name directly, but
  it confirms the project exists and leaks branch build state.
- **CONFIG_GAP** finding. The risk is information disclosure: a competitor
  or attacker can see whether your builds are passing, infer release
  cadence, and time attacks around known broken-build windows.
- If the badge is intentionally used for a public OSS project README →
  note as expected, but still emit the finding (the leak is real even if
  intentional).

### Step 7: Other configuration gaps

- **7a. Forensics gap.** If `logsConfig.cloudWatchLogs.status: DISABLED`
  AND `s3LogsConfig.status: DISABLED` → **CONFIG_GAP**. No build logs are
  captured. Incident response has no signal — a compromised build leaves
  no trace. At least one logs destination must be enabled.
- **7b. CloudWatch log group KMS.** If `cloudWatchLogs.status: ENABLED`
  and the log group has no KMS key associated (CloudWatch Logs
  server-side encryption is default but not customer-managed) →
  **CONFIG_GAP** sub-finding. Use `aws logs associate-kms-key` on the
  build log group.
- **7c. FileSystem locations.** If `fileSystemLocations` is non-empty and
  any entry's `identifier` references an EFS without an account-scoped
  filesystem policy → **CONFIG_GAP** sub-finding.
- **7d. Cache bucket exposure.** If `cache.type: S3` and the cache bucket
  has BLOCK_PUBLIC_ACCESS off → **CONFIG_GAP**. Cache poisoning is a
  supply-chain vector.
- **7e. ECR scan-on-push for built images.** If the inline buildspec runs
  `docker push` to an ECR repository and the ECR repo has
  `scanOnPush: false` → **CONFIG_GAP** sub-finding. The build produces
  unscanned images that downstream services deploy blindly. The fix is on
  the ECR repo, not the CodeBuild project:
  `aws ecr put-image-scanning-configuration --repository-name <r> --image-scanning-configuration scanOnPush=true`.

### Step 8: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all dimensions, where
PRIVILEGED > SECRET_LEAK > NO_ENCRYPTION > OVERPERMISSIVE_ROLE >
CONFIG_GAP > OK:

```text
verdict = max(step1, step2, step3, step4, step5, step6, step7)
```

If no findings, verdict is **OK**.

## Output format (per project)

```text
PROJECT: <name>
VERDICT: PRIVILEGED | SECRET_LEAK | NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [PRIVILEGED] <finding description (Step Na)>
  - [CONFIG_GAP] <finding description (Step Nb)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — privileged build with plaintext secret

```text
PROJECT: payments-ci
VERDICT: PRIVILEGED
REASON: environment.privilegedMode is true and the inline buildspec contains
no Docker commands (Step 1) — host-equivalent container privilege with no
Docker justification. Also leaks DB_PASSWORD in plaintext env vars.
FINDINGS:
  - [PRIVILEGED] privilegedMode true with non-Docker buildspec (Step 1)
  - [SECRET_LEAK] environmentVariables[DB_PASSWORD] type=PLAINTEXT (Step 2)
  - [OVERPERMISSIVE_ROLE] service role grants s3:* on "*" (Step 4c)
REMEDIATION:
  1. Disable privilegedMode (full-environment JSON replace):
     aws codebuild batch-get-projects --names payments-ci --query 'projects[0].environment' --output json > /tmp/env.json
     edit /tmp/env.json to set "privilegedMode": false
     aws codebuild update-project --name payments-ci --environment file:///tmp/env.json
  2. Move DB_PASSWORD to Secrets Manager: create the secret, then edit
     the same /tmp/env.json to drop the plaintext entry and add it to
     the secretsManager array, then re-apply update-project.
  3. Scope the service role's s3 actions to the specific bucket ARN.
```

## Edge-case handling

All six edge cases (partial malformation, buildspec filename reference, duplicate env vars, cross-account service role, unprovisioned log location, PUBLIC_READ quarantine): [Advanced patterns](references/advanced-patterns.md).

## Anti-Patterns — NEVER

- NEVER classify `privilegedMode: true` on a Docker-build project as
  PRIVILEGED. DinD requires privileged mode; the flag is the documented
  mechanism. Verify the buildspec before flagging.

- NEVER classify `type: PARAMETER_STORE` or `type: SECRETS_MANAGER`
  environment variables as SECRET_LEAK. These store only ARN references;
  the value is fetched at build time and never appears in the project
  config. The leak channel is closed by design.

- NEVER flag the absence of `kmsKeyArn` on `s3LogsConfig` as NO_ENCRYPTION
  when `encryptionDisabled` is also false and SSE-S3 default encryption
  is the documented organizational baseline. Re-read the org policy
  before flagging — some orgs explicitly accept SSE-S3 for build logs.

- NEVER treat a CodeBuild service role's `codebuild:*` on the project
  ARN as over-permissive. CodeBuild projects REQUIRE `codebuild:CreateReport`,
  `codebuild:UpdateReport`, `codebuild:BatchPut*` to function. These are
  baseline permissions, not wildcards.

- NEVER recommend deleting a project as remediation without snapshotting
  the config first. `delete-project` is irreversible; project configs are
  not versioned. Run `aws codebuild batch-get-projects --names <n> --output json`
  to a backup file first.

- NEVER assume the inline buildspec matches the source-repo buildspec.
  If `source.buildspec` is set, the inline YAML wins — the repo's
  `buildspec.yml` is IGNORED. A PR that modifies the repo buildspec has
  no effect when the inline override is in place. This is a SECURITY
  BENEFIT (deterministic buildspec), not a config gap.

- NEVER flag `concurrentBuildLimit` or `queuedRetry` as findings. These
  are operational knobs, not security posture.

- NEVER assume `vpcConfig` presence equals isolation. A VPC with public
  subnets provides zero isolation over the default network. The
  subnet-route-table check (Step 5b) is what determines real isolation.

- NEVER recommend flipping `encryptionDisabled: true` to false on a
  legacy cross-account artifacts setup without explaining the migration
  path. The setting exists because cross-account SSE-KMS used to require
  it. The fix is a customer-managed KMS key with a key policy granting
  the cross-account principal `kms:Decrypt`.

- NEVER classify `badgeEnabled: true` as anything other than CONFIG_GAP.
  It is information disclosure, not a privilege escalation. Downgrading
  the verdict because the project is "internal" misses the point — the
  badge URL is publicly reachable without auth.

- NEVER skip the service-role trust policy check. The trust policy
  determines WHO can assume the role; an unscoped trust policy is the
  confused-deputy vector that lets any CodeBuild project in the account
  use this role.

- NEVER assume the AWS-managed CodeBuild image runs as root. The default
  `aws/codebuild/standard:*` images run as the non-root `codebuild-user`.
  A `user: root` finding requires either a custom image with `USER root`
  or an explicit `user` override in the project config (which CodeBuild
  does not expose — it is image-driven).

- NEVER treat a missing service-role policy document as an
  OVERPERMISSIVE_ROLE finding. You cannot statically classify what you
  cannot see. Output a NOTE and require the operator to provide the
  policy. Guessing produces false positives.

- NEVER recommend `projectVisibility: PUBLIC_READ` as a way to "share a
  build with a partner account." Use a cross-account IAM role assumption
  instead. PUBLIC_READ makes the project startable by EVERY AWS account,
  not just the partner.

- NEVER overlook the cache bucket. `cache.type: S3` creates an S3 bucket
  that the build reads and writes on every run. If that bucket has public
  access or is in a different account, the cache is a supply-chain
  poisoning vector. Always verify S3 Block Public Access is ON for the
  cache bucket: `aws s3api get-public-access-block --bucket <b>`. A
  poisoned cache (a tampered `.tar` archive) executes arbitrary code in
  every subsequent build that unpacks it — a SolarWinds-style upstream
  vector.

- NEVER conflate `environment.image` (the build container image) with
  `source` (the Git repo). The image determines what runs; the source
  determines what gets built. A clean image + malicious source is a
  compromised build; a malicious image + clean source is a compromised
  build environment.

- NEVER allow wildcard actions in the service-role TRUST policy
  (`assumeRolePolicyDocument`). The Principal must be
  `{"Service": "codebuild.amazonaws.com"}` (singular, service-scoped) —
  never `{"AWS": "*"}` or `{"AWS": "arn:aws:iam::cloudroot"}`. The
  Condition must include `aws:SourceArn` or `aws:SourceAccount` scoped to
  the project — without it, ANY CodeBuild project in the account (or any
  principal if `{"AWS": "*"}`) can assume the role. This is the confused-
  deputy vector that the console-generated trust policy omits by default.

- NEVER treat `source.auth.resource` as the credential itself. It is a
  CodeBuild-generated ARN referencing a server-side stored token. The
  token is not in the project config; you cannot rotate it from
  `update-project`. Rotate via `aws codebuild import-source-credentials`
  with a fresh token, or sever the connection and re-import.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-project`, `delete-project`, `put-role-policy`,
  `create-project`), the auditor MUST emit:
  `CONFIRM: About to <action> on project <name> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. This gate
  prevents automated pipelines from silently modifying build projects.

Snapshot/verify commands (project-config backup, role-policy backups, in-flight build check, secret resolvability, additive-first preference): [Diagnostic commands](references/diagnostic-commands.md).

## Remediation guidance

**Ordering principle:** additive before destructive. Add a scoped
statement BEFORE removing a wildcard one. Add a condition BEFORE removing
an unconditional principal.

Full per-verdict remediation sequences with exact CLI (PRIVILEGED, SECRET_LEAK, NO_ENCRYPTION, OVERPERMISSIVE_ROLE, CONFIG_GAP, OK): [Error handling](references/error-handling.md).

## Deep reference: CodeBuild internals

Internals (build-host isolation, secrets-resolution pipeline, fleet multi-tenancy, config versioning, webhook scope, badge URL structure): [Advanced patterns](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

2024-2026 feature notes (macOS fleets, GitLab integration, Lambda compute, fleet VPC): [Advanced patterns](references/advanced-patterns.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — mindset facts, Step 0 expert knowledge, edge cases, CodeBuild internals, recent features
- [Diagnostic commands](references/diagnostic-commands.md) — pre-flight snapshot/verify commands
- [Error handling](references/error-handling.md) — per-verdict remediation sequences

## Domain

AWS CloudOps / Developer Tools (CodeBuild) Security & Compliance.

## AWS documentation

- **AWS CodeBuild User Guide** — https://docs.aws.amazon.com/codebuild/latest/userguide/welcome.html
- **CodeBuild Security** — https://docs.aws.amazon.com/codebuild/latest/userguide/security.html
- **CodeBuild API Reference** — https://docs.aws.amazon.com/codebuild/latest/APIReference/
- **CodeBuild CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/codebuild/
