---
name: ecr-repository-auditor
description: >-
  Audits AWS ECR private repositories for public-access exposure via
  repositoryPolicy, image-scan configuration gaps (scanOnPush off + unscanned
  images), lifecycle-policy absence, tag-immutability gaps, and encryption
  posture. Emits a deterministic verdict (PUBLIC | NO_SCAN | NO_LIFECYCLE |
  CONFIG_GAP | OK) per repository with enumerated findings and specific CLI
  remediation. Use when reviewing ECR repository policies, checking for public
  image access, validating scan-on-push enablement, auditing lifecycle rules,
  or hardening container-image supply-chain posture before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config classification. Live-account
  audits use aws ecr describe-repositories, aws ecr get-repository-policy,
  aws ecr describe-images, aws ecr get-lifecycle-policy, and
  aws ecr put-image-scanning-configuration (AWS CLI v2, SSO or key-based
  credentials).
keywords:
  - ECR
  - container registry
  - repository policy
  - scanOnPush
  - image scanning
  - lifecycle policy
  - tag immutability
  - Principal:"*"
  - cross-account ECR
  - supply chain security
  - container image audit
  - unscanned images
  - ecr:GetDownloadUrlForLayer
  - ecr:BatchGetImage
  - ecr:PutImage
  - aws:SourceVpce
  - image vulnerability
  - KMS encryption ECR
  - ECR public access
tags: [ecr, storage, security, container, supply-chain, image-scanning, lifecycle, tag-immutability, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Storage
  verdict_shape: "PUBLIC | NO_SCAN | NO_LIFECYCLE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an ECR repository before production deployment, checking for
    public image access via repositoryPolicy, validating scan-on-push
    enablement, auditing lifecycle-policy coverage, hardening tag immutability,
    or assessing container supply-chain posture across an account.
  activation_triggers:
    - "audit this ECR repository"
    - "is my ECR repo public"
    - "check ECR repository policy"
    - "ECR scanOnPush enabled"
    - "ECR lifecycle policy"
    - "unscanned container images"
    - "tag immutability check"
    - "ECR cross-account access"
    - "container image vulnerability scan"
    - "hardening ECR repository"
  invocation_schema: >-
    Input: either (a) an ECR repository configuration bundle (repositoryPolicy
    JSON + imageScanningConfiguration + imageTagMutability + lifecyclePolicyText
    + image metadata), OR (b) a repository name/ARN for live-account audit.
    Output: deterministic REPO/VERDICT/REASON/FINDINGS/REMEDIATION block per
    repository, where VERDICT is one of {PUBLIC, NO_SCAN, NO_LIFECYCLE,
    CONFIG_GAP, OK}.
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

**Multi-repo / account-wide sweep note (pagination):** when auditing every
repo in an account, `aws ecr describe-repositories` returns at most 100 per
page via `--max-results`. Use `--next-token` to page through all repositories;
iterating only the first page silently skips repos in other lifecycle stages.
For each repo, also page `aws ecr describe-images --repository-name <name>`
(caps at 100/page) and `aws ecr get-lifecycle-policy-preview` — both silently
truncate. Always drain `nextToken` to completion.

**Live-account pre-flight checks (skip if doing offline config audit):**
1. Verify the caller's identity can run `ecr:PutImageScanningConfiguration` and
   `ecr:PutLifecyclePolicy` if remediation is intended — most read-only auditor
   roles CANNOT, and remediation commands will fail with `AccessDenied`.
   Surface this BEFORE the operator approves the change.
2. Verify CloudTrail is logging ECR data events (`DeleteImage`, `PutImage`) —
   ECR management events (`CreateRepository`, `DeleteRepository`) are on by
   default, but `PutImage`/`BatchDeleteImage` are data events that must be
   explicitly enabled on the trail. Without them, image-tampering forensics
   have no signal.
3. Snapshot `aws ecr describe-images --repository-name <name>` BEFORE any policy
   edit — image digests and tags are not versioned. A PutImage overwrites a tag
   with no history. Compare pre/post to detect tag mutations during the
   remediation window.

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

- **ECR Private vs ECR Public are different services.** ECR Private
  (`api.ecr.<region>.amazonaws.com`) uses the `ecr` namespace and IAM
  policies. ECR Public (`public.ecr.aws`, `api.ecr-public.amazonaws.com`) uses
  the `ecr-public` namespace and is designed for public image distribution.
  This skill audits **private** repositories. If the input references
  `ecr-public` actions or a public registry alias, note that ECR Public has
  no repositoryPolicy-based access control — public visibility is governed by
  registry-level catalog data.

- **`ecr:GetAuthorizationToken` is account-scoped, not repo-scoped.** It
  returns a temporary auth token for the ENTIRE registry (all repos in the
  account). It cannot be restricted via `repositoryPolicy` `Resource` to a
  single repo — any IAM grant of `ecr:GetAuthorizationToken` exposes the
  registry auth token. A repositoryPolicy that includes
  `ecr:GetAuthorizationToken` in its Action list is misleading; this action
  is evaluated at the IAM level, not the repo-policy level. Do NOT use its
  presence in a repo policy to escalate the verdict.

- **`repositoryPolicy` and IAM identity-based policy follow the SAME-account
  union / cross-account intersection rule** as S3 and KMS resource-based
  policies. For same-account access, EITHER the repo policy OR the IAM policy
  can grant access (union). For cross-account access, BOTH must allow
  (intersection). This means an empty repositoryPolicy is SECURE for
  same-account (IAM governs) but BLOCKS all cross-account access.

- **`aws:SourceVpce` is the strongest condition for ECR.** A VPC endpoint ID
  (`vpce-abc123`) is assigned by AWS infrastructure and cannot be forged by
  the caller. It restricts access to traffic arriving through a specific
  PrivateLink endpoint. `aws:SourceVpce` is STRONGER than `aws:SourceIp`
  because it is tied to network infrastructure, not a routeable IP. When
  present with `StringEquals`, downgrade from PUBLIC to CONFIG_GAP per Step 1e — the
  access is fragile but currently scoped to known infrastructure.

- **`scanOnPush` only triggers on push, not on CVE database updates.** An
  image scanned on push is scanned against the vulnerability database AS OF
  the push timestamp. If a new CVE is disclosed tomorrow, the image is NOT
  automatically re-scanned. Enhanced scanning (Amazon Inspector integration)
  provides continuous re-scanning. A repo with `scanOnPush: true` but basic
  (non-enhanced) scanning has STALE vulnerability data for any image older
  than the last manual scan.

- **Lifecycle policy `rulePriority` is evaluated lowest-number-first, first
  match wins.** Once an image matches a rule, no lower-priority rule applies.
  A common misconfiguration: a rule that deletes ALL images after N days at
  priority 1, followed by a rule that retains the last 5 tagged images at
  priority 2 — the priority-1 rule deletes everything (including the last 5)
  before priority-2 is ever evaluated. The rule that should be most selective
  must have the LOWEST priority number.

- **`tagStatus: untagged` is the ONLY lifecycle rule that cleans up untagged
  images.** Without it, untagged images (images pushed without a tag, or
  images whose tags were all deleted) persist indefinitely. Untagged images
  are invisible to `describe-images --filter tagStatus=TAGGED` but still
  consume storage billing and count against the per-repo image quota.

- **`imageScanStatus: null` means NEVER scanned.** An image with no
  `imageScanStatus` field (or `imageScanStatus.status: "PENDING"`) has never
  been scanned by ECR. This is the signal for NO_SCAN, not `scanStatus` on the
  repository (which reflects the scanning configuration, not per-image state).
  Always enumerate images and check per-image scan status, not just the repo
  config.

- **Repository policy size limit follows IAM policy limits (10,240 chars for
  resource-based).** A policy with many statements can hit this cap. When
  proposing additive Deny statements as remediation, estimate cumulative
  size — prefer fewer, broader statements if near the cap.

- **`ecr:BatchDeleteImage` deletes by tag OR digest.** A principal with
  `ecr:BatchDeleteImage` can delete any image in the repo, including
  production images, by referencing the digest directly. Treat it as a
  destructive action equivalent to `ecr:PutImage` for overwriting risk.

- **`ecr:PutImage` is the tag-overwrite primitive.** With mutable tags, a
  principal with `ecr:PutImage` can push a new manifest under an existing tag
  (`:latest`, `:prod`), silently changing what `docker pull` returns. This is
  the core supply-chain attack vector for mutable-tag repos.

- **`ecr:StartImageScan` / `ecr:StartLifecyclePolicyPreview` are separate
  actions.** A repo policy that grants `ecr:Describe*` but not
  `ecr:StartImageScan` means images cannot be manually scanned by callers who
  rely only on the repo policy. Check whether the scanning workflow needs
  `StartImageScan` when designing least-privilege repo policies.

- **Cross-region replication is registry-level, not repo-level.** `aws ecr
  put-replication-configuration` replicates ALL repos to target regions. A
  public repository policy on a source repo propagates to replicas — the
  replica inherits the source's repositoryPolicy. Auditing only the source
  misses that the public exposure is now multi-region.

- **Pull-through cache rules** (`aws ecr put-pull-through-cache-rule`) create
  upstream-registry-backed repos. These repos are created on first pull and
  inherit the caller's permissions, not a pre-configured repositoryPolicy.
  Do not audit a pull-through-cache-created repo with the same logic as a
  manually created repo — its lifecycle is managed by the cache rule.

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

### For PUBLIC — wildcard/cross-account pull or push (Step 1a-1d)

1. **Immediately** remove the wildcard or cross-account principal from the
   repositoryPolicy, or add a strong condition (`aws:SourceVpce`,
   `aws:SourceAccount`, `aws:SourceArn`) to scope the grant.
   ```bash
   # Back up the current policy
   aws ecr get-repository-policy --repository-name <name> --registry-id <id> \
     --output json > /tmp/<name>-policy-backup.json

   # Apply the tightened policy (provide the new policy document)
   aws ecr set-repository-policy --repository-name <name> --registry-id <id> \
     --policy-text file://new-policy.json
   ```
2. **Assume breach.** Audit CloudTrail for `ecr:BatchGetImage` and
   `ecr:GetDownloadUrlForLayer` events from external principals during the
   exposure window. Any image they pulled should be considered inspected —
   rotate secrets found in image layers and rebuild images with a clean base.
3. If cross-account pull is **intentional** (e.g., a shared services account),
   replace `Principal: "*"` with the specific external role ARN and add
   `aws:SourceAccount` / `aws:SourceArn` conditions.

### For NO_SCAN — scanOnPush disabled or unscanned images (Step 2)

1. Enable scan-on-push:
   ```bash
   aws ecr put-image-scanning-configuration --repository-name <name> \
     --registry-id <id> --image-scanning-configuration scanOnPush=true
   ```
2. Manually scan existing unscanned images:
   ```bash
   for digest in $(aws ecr describe-images --repository-name <name> \
     --registry-id <id> --query 'imageDetails[?imageScanStatus==null].imageDigest' \
     --output text); do
     aws ecr start-image-scan --repository-name <name> --registry-id <id> \
       --image-id imageDigest=$digest
   done
   ```
3. For production repos, enable enhanced scanning (Amazon Inspector
   integration) for continuous re-scanning against the latest CVE database:
   ```bash
   aws ecr put-registry-scanning-configuration \
     --scanning-configuration scanType=ENHANCED,repositoryFilters=[{repositoryName=<name>}] \
     --profile <profile>
   ```
   Note: enhanced scanning is configured at the registry level, not per-repo.

### For NO_LIFECYCLE — no lifecycle policy (Step 3)

1. Create a lifecycle policy that retains the last N tagged images and deletes
   untagged images after 1 day:
   ```bash
   cat > /tmp/lifecycle.json << 'EOF'
   {
     "rules": [
       {
         "rulePriority": 1,
         "description": "Delete untagged images after 1 day",
         "selection": { "tagStatus": "untagged", "countType": "sinceImagePushed", "countUnit": "days", "countNumber": 1 },
         "action": { "type": "expire" }
       },
       {
         "rulePriority": 2,
         "description": "Keep last 10 tagged images",
         "selection": { "tagStatus": "any", "countType": "imageCountMoreThan", "countNumber": 10 },
         "action": { "type": "expire" }
       }
     ]
   }
   EOF
   ```
2. **Dry-run first** — verify which images would be deleted:
   ```bash
   aws ecr get-lifecycle-policy-preview --repository-name <name> --registry-id <id> \
     --policy-text file:///tmp/lifecycle.json --output json
   ```
3. Apply the policy:
   ```bash
   aws ecr put-lifecycle-policy --repository-name <name> --registry-id <id> \
     --lifecycle-policy-text file:///tmp/lifecycle.json
   ```

### For CONFIG_GAP — tag mutability (Step 4)

1. Set tag immutability:
   ```bash
   aws ecr put-image-tag-mutability --repository-name <name> \
     --registry-id <id> --image-tag-mutability IMMUTABLE
   ```
2. Verify:
   ```bash
   aws ecr describe-repositories --repository-names <name> --registry-id <id> \
     --query 'repositories[0].imageTagMutability' --output text
   ```

### For CONFIG_GAP — condition-restricted cross-account (Step 1e)

1. Validate the condition is still correct and the named VPC endpoint or
   account still exists.
2. Convert the Allow-based restriction to an explicit Deny (deny all except
   the trusted account/endpoint) — Deny statements cannot be accidentally
   widened by adding a new Allow.
3. For `aws:SourceVpce`, verify the VPC endpoint is still in use and has not
   been deleted (a deleted endpoint ID makes the condition unmatchable,
   silently blocking all access).

### For OK

1. No remediation required for the current posture.
2. Recommend enabling enhanced scanning if not already on (defense-in-depth
   for production repos).
3. Recommend adding a Deny statement for `aws:SecureTransport: false` to
   enforce TLS for all ECR API calls (defense-in-depth).
4. For repos with cross-region replication, verify replicas are also audited
   — they inherit the source repositoryPolicy.

## Deep reference: ECR authorization and scanning internals

### Repository policy vs IAM evaluation pipeline

ECR evaluates an access request in this order:

1. **Organizations SCP** — sets the maximum permissions. An SCP Deny blocks
   the request.
2. **Repository policy** (resource-based) — for same-account access, EITHER
   the repo policy OR the caller's IAM policy can allow (union). For
   cross-account access, BOTH must allow (intersection). This is identical to
   the S3 bucket policy evaluation model.
3. **IAM identity-based policy** — evaluated only if the repo policy does not
   independently grant or deny. For same-account, the union applies. For
   cross-account, the intersection applies.

Key consequence: an **empty** repositoryPolicy is SECURE for same-account
access because IAM governs everything. It also BLOCKS all cross-account
access because there is no resource-based Allow for the intersection. This
is why the default (no repo policy) is the most secure posture.

### Lifecycle policy rule evaluation

Rules are evaluated in `rulePriority` order (ascending — lowest number
first). For each image, the FIRST matching rule applies; no lower-priority
rule is evaluated for that image. This means:

- Rule priority 1 should be the most SELECTIVE rule (e.g., delete untagged
  images after 1 day).
- Rule priority 2+ should be progressively broader (e.g., keep last 10
  tagged images).
- A broad rule at priority 1 shadows ALL subsequent rules — images that
  match it are expired before any retention rule can protect them.

Lifecycle evaluation runs approximately once every 24 hours. Changes to the
policy are not applied immediately to existing images — they take effect at
the next evaluation cycle. Use `get-lifecycle-policy-preview` to test before
applying.

### Scanning internals — basic vs enhanced

- **Basic scanning:** ECR's native scanner. `scanOnPush: true` triggers a
  scan at push time against the vulnerability database AS OF the push. No
  re-scanning on CVE database updates. Findings are available via
  `describe-image-scan-findings`.
- **Enhanced scanning:** Amazon Inspector integration. Provides continuous
  re-scanning — images are re-evaluated when the Inspector CVE database is
  updated, not just at push time. Configured at the **registry** level via
  `put-registry-scanning-configuration`, not per-repo. Enhanced scanning
  incurs per-image-scanned costs.

A repo with `scanOnPush: true` and basic scanning has STALE vulnerability
data for any image older than the last CVE database update. This is not
flagged by the verdict (the repo IS scanning on push), but the auditor should
note the recommendation to enable enhanced scanning for production repos.

### KMS encryption internals

ECR supports three encryption types:
- **AES256** — AWS-managed key, no customer control over rotation or policy.
  Default if no encryptionConfiguration is specified.
- **KMS** — Customer-managed KMS key. The KMS key policy governs who can
  encrypt/decrypt image layers. Changing the KMS key after images are pushed
  does NOT re-encrypt existing images — they remain encrypted under the
  original key.
- **KMS_DSSE** — Double-layer encryption (KMS + AES256). Provides the highest
  encryption posture for compliance-sensitive workloads. Available in select
  regions.

The encryption type is set at **repository creation** and CANNOT be changed
after creation. To migrate encryption types, create a new repo with the
desired encryption, re-push images, and update pull references.

### Cross-region replication policy propagation

`put-replication-configuration` replicates ALL repositories in the source
region to target regions. The replication copies:
- Image content (layers, manifests)
- Repository policy (the full `repositoryPolicyText`)
- Scan configuration (`scanOnPush`)

The replication does NOT copy:
- Lifecycle policy (each replica manages its own lifecycle)
- Tag immutability setting (each replica manages its own)

This means a PUBLIC repository policy on the source propagates to all
replicas automatically. If you tighten the source policy, the replicas are
updated on the next replication cycle. Audit replicas independently.

## Domain

AWS CloudOps / ECR Container Registry Security & Supply-Chain Compliance.
