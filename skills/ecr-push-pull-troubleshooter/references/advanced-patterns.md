# ECR Push/Pull Troubleshooter — advanced patterns (moved from SKILL.md

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).
## Mindset (moved from SKILL.md)

A failing ECR push or pull is almost always an identity, policy, or
lifecycle incident, not a docker problem. Docker is the messenger —
the error string it surfaces is almost always the AWS-side denial
translated into docker terms. Senior container engineers do not start
by rebuilding the image; they start with `aws ecr get-authorization-token`,
the repository policy, and the lifecycle policy, and only rebuild once
auth, policy, and lifecycle are proven correct.

## Philosophy (moved from SKILL.md)

Four behaviours separate a senior ECR engineer from a generalist:

- **The auth token is base64(username:password) and valid for 12 hours.**
  The decoded token's username is the literal string `AWS` and the
  password is a signed STS-style URL query string. After 12 hours the
  signature expires and every push/pull fails with `Your authorization
  token has expired`. CI pipelines that cache the token in
  `~/.docker/config.json` longer than 12 hours hit this deterministically
  once a day. The fix is to refresh the token before every build, not
  to extend the token.
- **Cross-account access requires BOTH sides.** The caller's
  identity-based policy must allow `ecr:BatchGetImage` and friends on
  the target repository ARN, AND the target repository's resource-based
  policy must list the caller's account (`aws:PrincipalAccount`) or ARN.
  Operators who "added the IAM permission to the CI role" but still see
  `denied` from a cross-account pull always missed the repository
  policy side.
- **Lifecycle policy is first-match-wins, evaluated top to bottom.** A
  broad `expire` rule placed above a narrower `keep` rule deletes what
  the `keep` rule would have protected. Operators who "set a 10-image
  retention rule" and lost images they needed almost always had an
  earlier rule match first.
- **The registry alias, the account ID, and the region are three
  different things.** `public.ecr.aws/<alias>/repo` is ECR Public;
  `<account>.dkr.ecr.<region>.amazonaws.com/repo` is ECR Private.
  `docker push public.ecr.aws/...` when the target was a private URI
  silently pushes to a different registry and the next pull fails with
  `manifest unknown`.

## Step 0: Non-obvious behaviours that change diagnosis (moved from SKILL.md)

- **The auth token is the same password for all repositories in the
  registry.** `aws ecr get-login-password` returns one password scoped
  to the registry (`<account>.dkr.ecr.<region>.amazonaws.com`). Logging
  in once authorises push/pull to every repository in that registry —
  there is no per-repository login. A different region OR a different
  account is a different registry and needs a separate login.
- **The token in `~/.docker/config.json` is cached indefinitely by
  default.** Docker does not refresh the token; the cached entry stays
  until the next `docker login` overwrites it. A CI runner that caches
  `~/.docker/config.json` between jobs hits `Your authorization token
  has expired` deterministically once the 12-hour window elapses.
- **Repository policy and IAM policy combine with explicit-deny-wins.**
  An explicit `Deny` in either the IAM policy, the repository policy,
  or an SCP overrides any `Allow`. Implicit deny (no matching
  statement) in either policy also fails. For same-account access, IAM
  alone is sufficient; for cross-account, the repository policy must
  ALSO allow.
- **Lifecycle policy evaluation is first-match-wins, top to bottom.**
  Once a rule matches, its action (`expire`) is taken and no further
  rule is evaluated for that image. A broad `expire` rule placed above
  a narrower `keep` rule deletes images the `keep` rule would have
  protected. Always read rule order.
- **Tag immutability blocks overwrites, not first-push.** A new tag
  always succeeds; an existing tag always fails when `IMMUTABLE`.
  Switching mutability is per-repository and takes effect immediately.
- **Cross-region replication is asynchronous and eventually consistent.**
  After a push to the source region, the replica may take seconds to
  minutes to appear. A pull in the destination region before
  replication completes fails with `manifest unknown`. Replication
  rules do NOT replicate across accounts unless the destination is in
  the rule.
- **Scan-on-push findings do not block the push; they block the
  deploy.** ECR accepts the image, then runs the scan asynchronously.
  The push succeeds; a downstream CD gate reads
  `describe-image-scan-findings` and refuses to promote. Operators who
  say "the push was blocked by a CVE" almost always had a downstream
  gate do the blocking.
- **`describe-images` may briefly show a deleted image.** After a
  lifecycle `expire`, the image is marked for deletion and may still
  appear for up to 24 hours, then vanishes. CloudTrail `BatchDeleteImage`
  events from the ECR service principal are the actual delete record.
- **Image architecture is a property of the manifest, not the tag.**
  A tag like `app:v1` can point to a single-arch image (`linux/amd64`)
  or a multi-arch manifest list. A Fargate task on `x86_64` pulling a
  tag that resolves to a single-arch `arm64` image fails with `no
  matching manifest for platform linux/amd64 in the manifest list` (if
  multi-arch) or `failed to register layer: ...` (if single-arch arm64
  forced onto x86).

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Pull-through cache for ECR Private (2024-2025):** Rules cache images from upstream registries (Docker Hub, Quay, ECR Public) on first pull. Common misconfigurations: prefix mismatches and upstream secret expiry.
- **ECR scan engine integration with Inspector (2024-2025):** Enhanced scan delegates to Amazon Inspector for deeper CVE coverage. Downstream gates may consume either source.
- **Lifecycle policy preview (2024-2025):** `start-lifecycle-policy-preview` dry-runs a policy and returns the would-be deletions. Always preview before applying a new policy.
- **Registry alias for ECR Public (2024):** Custom aliases; collisions produce REGISTRY_ALIAS_MISMATCH-class errors. Verify alias ownership via `ecr-public describe-registries`.
- **Fargate arm64 (Graviton) GA (2024):** Fargate supports `runtimePlatform: ARM64` on platform version 1.4.0+. A mismatch between task platform and image architecture fails the pull.
