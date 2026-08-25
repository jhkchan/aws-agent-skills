# Advanced Patterns (load on demand) — ECR Repository Auditor

Step 0 expert-knowledge deep dives, ECR authorization and scanning internals, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0: Expert knowledge — non-obvious ECR behaviors (moved from SKILL.md)

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

## Deep reference: ECR authorization and scanning internals (moved from SKILL.md)

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

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **ECR Enhanced Scanning (2024-2025):** ECR Enhanced Scanning now uses Amazon Inspector to scan for both OS package vulnerabilities and language package vulnerabilities (Python, Java, Node.js, etc.). Auditors should verify that `scanType` is set to `ENHANCED` (not `BASIC`) on production repositories — basic scanning only covers OS packages.
- **Pull-through cache rules (2024):** ECR pull-through cache allows pulling images from upstream registries (Docker Hub, Quay, public ECR) and caching them locally. Auditors should verify that pull-through cache repositories have appropriate lifecycle policies — cached images can accumulate without cleanup.
- **Replication across regions/accounts (2024):** ECR cross-region and cross-account replication is now GA. Auditors should verify that replicated repositories in other regions/accounts have equivalent security policies (scan-on-push, tag immutability, lifecycle).
- **Lifecycle policy enhancements (2024):** Improved lifecycle policy rules with more filtering options. Auditors should verify that lifecycle policies cover untagged images and that the policy does not accidentally delete production images.
