---
name: ecr-repository-auditor
description: Audits AWS ECR private repositories for public-access exposure via repositoryPolicy, image-scan configuration gaps (scanOnPush off + unscanned images), lifecycle-policy absence, tag-immutability gaps, and encryption posture. Emits a deterministic verdict (PUBLIC | NO_SCAN | NO_LIFECYCLE | CONFIG_GAP | OK) per repository with enumerated findings and specific CLI remediation. Use when reviewing ECR repository policies, checking for public image access, validating scan-on-push enablement, auditing lifecycle rules, or hardening container-image supply-chain posture before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline config classification. Live-account audits use aws ecr describe-repositories, aws ecr get-repository-policy, aws ecr describe-images, aws ecr get-lifecycle-policy, and aws ecr put-image-scanning-configuration (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  verdict_shape: PUBLIC | NO_SCAN | NO_LIFECYCLE | CONFIG_GAP | OK
  when_to_use: Reviewing an ECR repository before production deployment, checking for public image access via repositoryPolicy, validating scan-on-push enablement, auditing lifecycle-policy coverage, hardening tag immutability, or assessing container supply-chain posture across an account.
  activation_triggers: audit this ECR repository, is my ECR repo public, check ECR repository policy, ECR scanOnPush enabled, ECR lifecycle policy, unscanned container images, tag immutability check, ECR cross-account access, container image vulnerability scan, hardening ECR repository
  invocation_schema: 'Input: either (a) an ECR repository configuration bundle (repositoryPolicy JSON + imageScanningConfiguration + imageTagMutability + lifecyclePolicyText + image metadata), OR (b) a repository name/ARN for live-account audit. Output: deterministic REPO/VERDICT/REASON/FINDINGS/REMEDIATION block per repository, where VERDICT is one of {PUBLIC, NO_SCAN, NO_LIFECYCLE, CONFIG_GAP, OK}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: ECR, container registry, repository policy, scanOnPush, image scanning, lifecycle policy, tag immutability, Principal:"*", cross-account ECR, supply chain security, container image audit, unscanned images, ecr:GetDownloadUrlForLayer, ecr:BatchGetImage, ecr:PutImage, aws:SourceVpce, image vulnerability, KMS encryption ECR, ECR public access
  tags: ecr, storage, security, container, supply-chain, image-scanning, lifecycle, tag-immutability, audit
---

# ECR Repository Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across all
dimensions, and `repositoryPolicy` with `Principal: "*"` is the dominant
finding — a public container image is a supply-chain attack surface that
silently spreads to every downstream deployment.

An ECR private repository is the source of truth for container images that
production workloads pull and execute. Three properties make ECR audit
distinct from S3 or KMS:
- A **public repository policy** (`Principal: "*"`) grants the entire internet
  permission to pull images — and anyone who can pull can inspect every layer
  for embedded secrets, application logic, and dependency versions.
- **scanOnPush: false** creates a vulnerability blind spot: images enter the
  registry unscanned, and without a lifecycle policy, stale unscanned images
  accumulate indefinitely.
- **Tag mutability** (`MUTABLE`) is a supply-chain integrity risk: any principal
  with `ecr:PutImage` can overwrite a production tag (`:latest`, `:v2`) with a
  different image digest, silently swapping what deployments pull.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `Principal: "*"` + pull/push action + no STRONG condition | **PUBLIC** | Step 1 |
| Cross-account + pull/push action + no STRONG condition | **PUBLIC** | Step 1 |
| `Principal: "*"` + pull/push action + STRONG condition (`aws:SourceVpce`, `aws:SourceAccount`) | **CONFIG_GAP** | Step 1 (downgrade) |
| `imageScanningConfiguration.scanOnPush: false` AND images with `imageScanStatus` null/incomplete | **NO_SCAN** | Step 2 |
| `scanOnPush: false` AND zero images in repo | **NO_SCAN** | Step 2 |
| No `lifecyclePolicyText` present | **NO_LIFECYCLE** | Step 3 |
| `imageTagMutability: MUTABLE` (all other dimensions clean) | **CONFIG_GAP** | Step 4 |
| Cross-account + metadata-only actions + no condition | **CONFIG_GAP** | Step 4 |
| All dimensions clean | **OK** | Step 5 |

See the ordered steps below for edge cases. Deep ECR authorization internals
(policy vs IAM intersection, lifecycle rule ordering, enhanced scanning) are in
the [Deep reference](#deep-reference-ecr-authorization-and-scanning-internals)
section at the end.

## Pre-flight: repository metadata gate (run before policy classification)

Before evaluating the repository policy, classify the repository itself.
Several attributes **short-circuit** the audit — misclassifying them produces
false positives.

Multi-repo / account-wide sweep pagination guidance moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when auditing every repository in an account (describe-repositories / describe-images / lifecycle-preview nextToken draining).

**Live-account pre-flight checks (skip if doing offline config audit):**
Live-account pre-flight checks (remediation IAM permissions, CloudTrail data events, pre-edit image snapshot) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before a live-account audit that may propose remediation.

| Attribute | Value | Effect on audit |
|---|---|---|
| `registryId` | account ID | The 12-digit account that owns the registry. Cross-account principal detection compares this against principal ARNs in the repositoryPolicy. |
| Empty repositoryPolicy | no policy document | **IAM-only access.** This is the DEFAULT and MOST SECURE posture for ECR private repos. No resource-based policy means access is controlled entirely by IAM identity-based policies. Do NOT flag as a gap — proceed to scan/lifecycle/tag steps. |
| `imageScanningConfiguration.scanOnPush` | `true` | Images are scanned automatically on push. Does NOT scan images pushed before this was enabled, nor re-scan on CVE database updates (unless enhanced scanning is on). |
| `imageScanningConfiguration.scanOnPush` | `false` | Images are NOT scanned on push. Manual `aws ecr start-image-scan` is required per image. Flag in Step 2 if unscanned images exist. |
| `imageTagMutability` | `IMMUTABLE` | Tags cannot be overwritten — each tag permanently maps to one digest. This is the secure default for supply-chain integrity. |
| `imageTagMutability` | `MUTABLE` | Tags CAN be overwritten — any principal with `ecr:PutImage` can push a new image under an existing tag, silently changing what deployments pull. Flag in Step 4. |
| `encryptionConfiguration.encryptionType` | `AES256` | Default encryption using an AWS-managed key. Acceptable but not customer-controlled. Note as informational. |
| `encryptionConfiguration.encryptionType` | `KMS` | Customer-managed KMS key (BYOK). Provides audit trail via CloudTrail and rotation control. |
| `encryptionConfiguration.encryptionType` | `KMS_DSSE` | Double-layer server-side encryption (KMS + AES256). Highest encryption posture. |
| `encryptionConfiguration.encryptionType` | absent | Defaults to `AES256`. Do not flag. |
| `lifecyclePolicyText` | absent / empty | No lifecycle rules. Images accumulate indefinitely — cost grows unbounded and stale images remain pullable. Flag in Step 3. |

**If the repositoryPolicy JSON is malformed** (invalid JSON, missing
`Statement`, missing `Principal` or `Action`/`NotAction`), output:

```text
REPO: <repo-name>
VERDICT: ERROR
REASON: Repository policy document is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical policy with `aws ecr get-repository-policy --repository-name <name> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious ECR behaviors that change classification

These behaviors are easy to misjudge without operational ECR experience.
Each changes a verdict if ignored:

Step 0 expert-knowledge behaviors moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a verdict depends on non-obvious behavior (private vs public, GetAuthorizationToken scope, union/intersection, SourceVpce strength, scan staleness, rulePriority order, untagged cleanup).

### Step 1: PUBLIC — repositoryPolicy exposure (highest priority)

For each `Effect: Allow` statement in the repositoryPolicy, classify the
principal and actions:

**Principal scope:**
- **WILDCARD_PRINCIPAL** — Principal is `"*"`, `{"AWS": "*"}`, or any
  construct resolving to all authenticated AWS principals.
- **CROSS_ACCOUNT** — Principal includes an ARN whose 12-digit account ID
  differs from the registry's owning account (`registryId`).
- **SAME_ACCOUNT** — All principals share the `registryId`. This includes
  the account root, same-account roles, users, and services.

**Action danger classification:**
- **PULL** — `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`,
  `ecr:BatchCheckLayerAvailability`, `ecr:DescribeImages`,
  `ecr:DescribeRepositories`, `ecr:GetDownloadUrlForLayer`. A principal with
  pull can download every layer — equivalent to reading all source code,
  secrets, and binaries.
- **PUSH** — `ecr:PutImage`, `ecr:InitiateLayerUpload`,
  `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`,
  `ecr:BatchDeleteImage`. A principal with push can inject malicious images
  or overwrite production tags.
- **ADMIN** — `ecr:*`, `ecr:DeleteRepository`,
  `ecr:PutRepositoryPolicy`, `ecr:SetRepositoryPolicy`. Full control of the
  repo including policy modification and deletion.
- **METADATA** — `ecr:Describe*`, `ecr:List*`, `ecr:GetRepositoryPolicy`.
  Read-only informational access. Low severity but still a data leak in
  aggregate (repo names, image counts, tags).

**Severity matrix for repositoryPolicy (apply in order, first match wins):**

| # | Principal | Action | Condition | Severity |
|---|---|---|---|---|
| 1a | WILDCARD_PRINCIPAL | PUSH or ADMIN | None/weak | **PUBLIC** |
| 1b | WILDCARD_PRINCIPAL | PULL | None/weak | **PUBLIC** |
| 1c | CROSS_ACCOUNT | PUSH or ADMIN | None/weak | **PUBLIC** |
| 1d | CROSS_ACCOUNT | PULL | None/weak | **PUBLIC** |
| 1e | WILDCARD or CROSS | PULL/PUSH | STRONG (`aws:SourceVpce`, `aws:SourceAccount`, `aws:SourceArn`) | **CONFIG_GAP** (downgraded — fragile but scoped) |
| 1f | WILDCARD or CROSS | METADATA only | None/weak | **CONFIG_GAP** |
| 1g | SAME_ACCOUNT | Any | Any | Not a PUBLIC finding (proceed to other steps) |

**Special case — the empty repositoryPolicy:** An ECR repo with no
`repositoryPolicy` (the default) has NO resource-based policy. This means
access is governed ENTIRELY by IAM identity-based policies. This is the
SECURE DEFAULT. Do NOT flag an empty repo policy as a gap — it is more
secure than a permissive one. Proceed to Steps 2-4.

**Special case — the account-root delegation statement:** A statement with
`Principal: {"AWS": "arn:aws:iam::ACCOUNT:root"}` + `ecr:*` (or any broad
action set) is the **root-delegation pattern**. It delegates repository
access control to the account's IAM identity-based policies — anyone with
the right IAM permissions can use the repo, anyone without cannot. This is
the NORMAL and EXPECTED pattern for ECR repos that rely on IAM for access
control. Do NOT flag it as CONFIG_GAP or any other finding. It is functionally
equivalent to the empty repositoryPolicy (both defer to IAM). Classify this
statement as SAME_ACCOUNT / OK (row 1g) and proceed to Steps 2-4. The only
exception: if the same statement ALSO includes a wildcard or cross-account
principal alongside the root principal — classify by the WIDEST principal
(row 1a-1f apply to the wildcard/cross-account portion).

**Special case — the account-root delegation statement:** A statement with
`Principal: {"AWS": "arn:aws:iam::ACCOUNT:root"}` + `ecr:*` (or any broad
action set) is the **root-delegation pattern**. It delegates repository
access control to the account's IAM identity-based policies — anyone with
the right IAM permissions can use the repo, anyone without cannot. This is
the NORMAL and EXPECTED pattern for ECR repos that rely on IAM for access
control. Do NOT flag it as CONFIG_GAP or any other finding. It is functionally
equivalent to the empty repositoryPolicy (both defer to IAM). Classify this
statement as SAME_ACCOUNT / OK (row 1g) and proceed to Steps 2-4. The only
exception: if the same statement ALSO includes a wildcard or cross-account
principal alongside the root principal — classify by the WIDEST principal
(row 1a-1f apply to the wildcard/cross-account portion).

**NotAction in an Allow statement** is an inverse wildcard — it grants every
ECR action EXCEPT the listed ones. Treat as ADMIN danger level (worst case)
because new ECR APIs are automatically included.

**Condition strength:**
- **STRONG (downgrade by two levels):** `aws:SourceVpce` (VPC endpoint ID —
  infrastructure-assigned, unforgeable), `aws:SourceAccount` with
  `StringEquals`, `aws:SourceArn` with `StringEquals`/`StringLike`.
- **WEAK (no downgrade):** `aws:SourceIp` / `aws:SourceIp` containing
  `0.0.0.0/0` (bypassable by anyone with a proxy or VPN; the entire internet
  if `0.0.0.0/0`), `aws:Referer`, `aws:UserAgent` (trivially forgeable).

### Step 2: NO_SCAN — image scanning gaps

Evaluate the scanning posture:

- **`scanOnPush: false` AND any image with `imageScanStatus: null` or
  `imageScanStatus.status` not `"COMPLETE"`** → **NO_SCAN**. Images are
  entering the registry without vulnerability scanning. Any CVE in a base
  image layer or dependency goes undetected.

- **`scanOnPush: false` AND the repo has zero images** → **NO_SCAN**. The
  repo is empty now, but the first image pushed will not be scanned.
  Remediate preemptively.

- **`scanOnPush: true` AND all images have `imageScanStatus.status:
  "COMPLETE"`** → OK for this dimension. Note: basic scanning (non-enhanced)
  does not re-scan on CVE database updates — recommend enhanced scanning for
  production repos.

- **`scanOnPush: true` AND some images have `imageScanStatus: null`** →
  **NO_SCAN**. These images were pushed before scanOnPush was enabled and
  were never manually scanned. Run `aws ecr start-image-scan` on each.

### Step 3: NO_LIFECYCLE — lifecycle policy absence

- **No `lifecyclePolicyText` present (empty string or absent field)** →
  **NO_LIFECYCLE**. Without lifecycle rules, images accumulate indefinitely.
  This means: (1) storage cost grows without bound, (2) stale images with
  known vulnerabilities remain pullable, (3) the repo approaches the
  per-repo image quota with no cleanup path.

- **`lifecyclePolicyText` present but contains only a `tagStatus: tagged`
  retention rule with no `tagStatus: untagged` rule** → still **NO_LIFECYCLE**
  (partial gap). Untagged images are not cleaned up. Emit a CONFIG_GAP-level
  note within the NO_LIFECYCLE finding: "Lifecycle policy exists but lacks an
  `untagged` cleanup rule — untagged images accumulate indefinitely."

- **`lifecyclePolicyText` present with at least one rule** → OK for this
  dimension. Verify the rule ordering (lowest `rulePriority` evaluated first)
  and that the rule set is logically sound (a broad early rule does not
  shadow a selective later rule).

### Step 4: CONFIG_GAP — tag immutability, encryption, and other config gaps

If Steps 1-3 produced no PUBLIC/NO_SCAN/NO_LIFECYCLE finding, evaluate
remaining configuration:

- **`imageTagMutability: MUTABLE`** → **CONFIG_GAP**. Tags can be overwritten
  by any principal with `ecr:PutImage`. A supply-chain attacker who
  compromises a CI/CD role can push a backdoored image under the `:prod` tag,
  and the next deployment pulls the malicious image with no visible change to
  the tag name. Immutable tags prevent this: each tag permanently maps to one
  digest.

- **Cross-account principal with METADATA-only actions and no condition** →
  **CONFIG_GAP**. Not PUBLIC (metadata only) but still an information leak
  (repo inventory, image counts, tag names).

- **Cross-account PULL/PUSH with STRONG condition (already downgraded from
  Step 1)** → the downgrade lands here as **CONFIG_GAP** (fragile but scoped).

- **`imageTagMutability: IMMUTABLE` + no other config gaps** → OK for this
  dimension.

### Step 5: Aggregation — worst finding wins

The final verdict is the **maximum severity** finding across all steps, where
PUBLIC > NO_SCAN > NO_LIFECYCLE > CONFIG_GAP > OK:

```text
verdict = max(step1_finding, step2_finding, step3_finding, step4_finding)
```

If no findings (all dimensions clean), the verdict is **OK**.

## Output format (per repository)

```text
REPO: <registry-id>.dkr.ecr.<region>.amazonaws.com/<repo-name>
VERDICT: PUBLIC | NO_SCAN | NO_LIFECYCLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [PUBLIC] <finding description (Step 1a)>
  - [NO_SCAN] <finding description (Step 2)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — public pull with scan off and no lifecycle

```text
REPO: 111111111111.dkr.ecr.us-east-1.amazonaws.com/app-frontend
VERDICT: PUBLIC
REASON: Statement "PublicPull" grants ecr:BatchGetImage and
ecr:GetDownloadUrlForLayer to Principal "*" with no condition — any AWS
account holder can pull every image layer, exposing source code and embedded
secrets (Step 1b). scanOnPush is also disabled with unscanned images present.
FINDINGS:
  - [PUBLIC] Principal "*" + PULL actions (BatchGetImage, GetDownloadUrlForLayer) with no condition (Step 1b)
  - [NO_SCAN] scanOnPush: false + 3 images with imageScanStatus: null (Step 2)
  - [NO_LIFECYCLE] No lifecyclePolicyText present (Step 3)
  - [CONFIG_GAP] imageTagMutability: MUTABLE (Step 4)
REMEDIATION:
  1. PUBLIC — Remove the "PublicPull" statement or add aws:SourceAccount /
     aws:SourceVpce conditions to scope to trusted accounts/endpoints only.
  2. NO_SCAN — Enable scan-on-push:
     aws ecr put-image-scanning-configuration --repository-name app-frontend
     --image-scanning-configuration scanOnPush=true --registry-id 111111111111
  3. NO_LIFECYCLE — Apply a lifecycle policy that keeps the last 10 tagged
     images and deletes untagged images after 1 day (see remediation CLI).
  4. CONFIG_GAP — Set tag immutability:
     aws ecr put-image-tag-mutability --repository-name app-frontend
     --image-tag-mutability IMMUTABLE --registry-id 111111111111
```

## Anti-Patterns — NEVER

- NEVER classify a `Principal: "*"` grant with `ecr:BatchGetImage` /
  `ecr:GetDownloadUrlForLayer` as anything other than PUBLIC when there is no
  STRONG condition. Pull permissions grant access to every image layer —
  equivalent to reading all source code, embedded secrets, and binaries.
  This is not "broad access" — it is total image exposure.

- NEVER flag an empty repositoryPolicy as a security gap. An ECR repo with no
  resource-based policy relies on IAM identity-based policies for access
  control — this is the **secure default** and more restrictive than a
  permissive policy. Flagging it as a gap causes unnecessary policy churn
  that can introduce exposure.

- NEVER flag `Principal: {"AWS": "arn:aws:iam::ACCOUNT:root"}` + `ecr:*` as
  a CONFIG_GAP or security finding. This is the **root-delegation statement**
  — it delegates repository access to the account's IAM policies, exactly
  like an empty repositoryPolicy but explicit. Without it, IAM-based access
  patterns still work (same-account union evaluation), but its presence is
  NOT a sign of over-permissive access. The root principal is the account
  owner; `ecr:*` to root means "the account owner can manage this repo via
  IAM." Flagging it as CONFIG_GAP is a false positive that produces alert
  fatigue. The equivalent in KMS is the root-of-trust statement — normal and
  required.

- NEVER flag `Principal: {"AWS": "arn:aws:iam::ACCOUNT:root"}` + `ecr:*` as
  a CONFIG_GAP or security finding. This is the **root-delegation statement**
  — it delegates repository access to the account's IAM policies, exactly
  like an empty repositoryPolicy but explicit. Without it, IAM-based access
  patterns still work (same-account union evaluation), but its presence is
  NOT a sign of over-permissive access. The root principal is the account
  owner; `ecr:*` to root means "the account owner can manage this repo via
  IAM." Flagging it as CONFIG_GAP is a false positive that produces alert
  fatigue. The equivalent in KMS is the root-of-trust statement — normal and
  required.

- NEVER treat `aws:SourceIp` with `0.0.0.0/0` as a real condition. This CIDR
  is the entire internet and provides zero restriction. Any principal with a
  proxy, VPN, or NAT gateway can route through an allowed CIDR. Treat the
  statement as if the condition is absent.

- NEVER treat `ecr:GetAuthorizationToken` in a repositoryPolicy as a
  meaningful grant. This action is account-scoped (returns a registry-wide
  auth token) and is evaluated at the IAM level, not the repo-policy level.
  Its presence in a repo policy is misleading — do NOT use it to escalate the
  verdict or classify as a PULL/PUSH/ADMIN action.

- NEVER classify a `Principal: "*"` grant with a STRONG condition
  (`aws:SourceVpce`, `aws:SourceAccount`, `aws:SourceArn`) as PUBLIC. The
  condition narrows access to a known endpoint or account. Downgrade to
  CONFIG_GAP. Classifying it as PUBLIC conflates "currently restricted" with
  "unrestricted" and produces alert fatigue.

- NEVER overlook `NotAction` in an Allow statement. `NotAction` grants every
  ECR action EXCEPT the listed ones — the inverse of the intended scope, and
  almost always a misconfiguration. Treat as ADMIN danger (worst case) because
  new ECR APIs are automatically included.

- NEVER assume `scanOnPush: true` means all images are scanned. Images pushed
  before scanOnPush was enabled are NOT retroactively scanned. Always
  enumerate images and check per-image `imageScanStatus` — the repo-level
  config reflects intent, not per-image reality.

- NEVER assume a lifecycle policy with `tagStatus: tagged` rules cleans up
  untagged images. Only a `tagStatus: untagged` rule deletes untagged images.
  Without it, untagged images persist indefinitely, consuming storage and
  counting against the image quota while being invisible to tag-based queries.

- NEVER recommend setting `imageTagMutability: IMMUTABLE` without warning
  that existing mutable tags remain mutable until overwritten. The setting
  applies to future tag operations only — a tag that was overwritten before
  the change keeps its current digest. Re-push affected images to pin the
  intended digest.

- NEVER ignore lifecycle policy `rulePriority` ordering. Rules are evaluated
  lowest-number-first and first-match-wins. A broad retention/deletion rule
  at priority 1 shadows all subsequent rules. The most selective rule must
  have the lowest priority number.

- NEVER assume cross-region replication does not propagate repository
  policies. ECR replication copies the source repo's repositoryPolicy to
  replicas in target regions. A public policy on a source repo is
  automatically multi-region. Audit replicas independently when replication
  is configured.

- NEVER confuse ECR Private with ECR Public. ECR Private
  (`api.ecr.<region>.amazonaws.com`) uses repositoryPolicy for access control.
  ECR Public (`public.ecr.aws`) uses catalog-level visibility — there is no
  per-repo policy for public access. This skill audits private repositories
  only.

- NEVER recommend deleting an ECR repository as remediation without first
  verifying that no running workloads pull from it. Repository deletion is
  irreversible — all images are permanently lost. Run `aws ecr describe-images`
  and check ECS/EC2/EKS task definitions for references before recommending
  deletion.

- NEVER classify a same-account-only repositoryPolicy with named principals
  as PUBLIC. Same-account access is governed by IAM identity-based policies
  (union evaluation), which provides a second authorization layer. Flag
  CONFIG_GAP at worst for same-account metadata-only cross-principal access.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (PutImageScanningConfiguration, PutLifecyclePolicy,
  PutImageTagMutability, DeleteRepositoryPolicy, DeleteRepository), the
  auditor MUST emit:
  `CONFIRM: About to <action> on repository <name> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **PutImageTagMutability is irreversible for existing tags.** Changing from
  MUTABLE to IMMUTABLE prevents future overwrites but does not restore
  previously overwritten tags. Changing from IMMUTABLE to MUTABLE re-enables
  overwrites for all tags. Warn the operator about both directions.

- **PutLifecyclePolicy can delete images immediately.** A lifecycle policy
  with `tagStatus: any` and `countNumberInList: 1` evaluates on the next
  lifecycle evaluation cycle (within ~24 hours) and can delete images
  matching the rule. ALWAYS run `aws ecr get-lifecycle-policy-preview` to
  dry-run the policy before applying it. The preview shows exactly which
  images would be deleted.

- Confirm the repository exists and is accessible:
  `aws ecr describe-repositories --repository-names <name> --registry-id <id>`
  — fail closed (skip remediation) if it returns an error.

- Capture the current configuration for rollback before any modification:
  ```bash
  aws ecr get-repository-policy --repository-name <name> --registry-id <id> \
    --output json > /tmp/<name>-policy-backup-$(date +%s).json
  aws ecr get-lifecycle-policy --repository-name <name> --registry-id <id> \
    --output json > /tmp/<name>-lifecycle-backup-$(date +%s).json
  ```

- For PUBLIC findings (wildcard principal with pull/push, no condition),
  treat as incident-response. Audit CloudTrail for `ecr:BatchGetImage` /
  `ecr:GetDownloadUrlForLayer` events from external principals during the
  exposure window. Any pulled image should be considered potentially
  inspected for embedded secrets — rotate any secrets found in image layers.

- Prefer additive changes (add a Deny statement, add a condition) over
  destructive changes (remove an Allow statement) — additive changes are
  reversible and do not risk breaking existing pull workflows. The safe
  sequence for a PUBLIC finding is: (1) back up policy, (2) add a Deny that
  blocks the wildcard principal, (3) verify the Deny is effective via policy
  preview, (4) only then remove the offending Allow statement.

## Remediation guidance

Per-verdict remediation guidance (PUBLIC, NO_SCAN, NO_LIFECYCLE, CONFIG_GAP, OK) with full CLI sequences moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when emitting REMEDIATION or before executing any state-changing CLI.

## Deep reference: ECR authorization and scanning internals

Deep ECR authorization and scanning internals moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the policy-vs-IAM evaluation pipeline, lifecycle rule evaluation, basic vs enhanced scanning, KMS encryption internals, and replication propagation.

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when auditing enhanced scanning, pull-through caches, replication, or lifecycle enhancements.

## References (load on demand)

- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight checks, multi-repo sweep pagination, and per-verdict remediation CLI sequences moved from SKILL.md.
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert-knowledge deep dives, ECR authorization and scanning internals, and recent AWS features moved from SKILL.md.

## Domain

AWS CloudOps / ECR Container Registry Security & Supply-Chain Compliance.

## AWS documentation

- **Amazon ECR User Guide** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html
- **ECR Security** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/security.html
- **ECR API Reference** — https://docs.aws.amazon.com/AmazonECR/latest/APIReference/
- **ECR CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/ecr/
- **Enhanced scanning with Amazon Inspector** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning-enhanced.html
