# Advanced Patterns (load on demand) — CloudFront Invalidation Operator

Operational heuristics moved verbatim from SKILL.md: the Step 0 non-obvious CloudFront invalidation behaviors and the 2024-2026 feature notes.


---

## Step 0: Expert heuristic — non-obvious CloudFront behaviors (moved from SKILL.md)

These behaviors are easy to misjudge without operational invalidation
experience. Each changes a plan if ignored:

- **`/*` counts as ONE path, not N paths.** The single most
  misunderstood invalidation cost fact. `/*` invalidates every object
  in the distribution but the billing system counts it as one path.
  This is always cheaper than listing more than one individual object
  path — and it is free for the first 1,000 `/*` invalidations per
  month.

- **Versioned filenames eliminate the need for invalidation.** If
  your build process appends a hash to asset names
  (`main.a1b2c3.js`), the new version is a different URL. CloudFront
  fetches it from the origin on first request. No invalidation
  needed. This is the AWS-recommended cache-busting strategy for
  routine deploys. Reserve invalidation for emergencies, hotfixes to
  unversioned HTML, or removal of sensitive content.

- **`CallerReference` is a deduplication key, not a description.**
  CloudFront uses `CallerReference` to ensure idempotency. If you
  reuse a CallerReference, CloudFront returns the PREVIOUS
  invalidation (if it exists) without creating a new one. This is a
  silent failure — the invalidation appears to succeed but does
  nothing new. Always use a unique value (UUID or timestamp).

- **Wildcard `*` matches only within a single path segment.**
  `/images/*.jpg` matches `/images/photo.jpg` but NOT
  `/images/thumbnails/photo.jpg`. There is no recursive wildcard.
  To invalidate a directory tree, use `/images/*` (matches
  everything under `/images/`).

- **Invalidation does NOT purge the browser cache.** CloudFront
  invalidation clears edge cache. End-user browsers still have their
  local cache. To force browser refresh, use versioned filenames or
  short `Cache-Control: max-age` values. Invalidation + long
  browser cache TTLs = stale content for users.

- **Continuous deployment requires invalidating BOTH distributions.**
  With a continuous deployment policy, traffic is split between
  primary and staging. An invalidation on the primary does not
  affect staging's edge cache (and vice versa). When testing a
  deployment, invalidate staging first; when promoting, invalidate
  the primary.

- **Invalidation does not roll back the origin.** If you deployed a
  broken build and invalidate `/*`, CloudFront will re-fetch the
  broken content from the origin. You must fix the origin (redeploy,
  rollback) BEFORE or SIMULTANEOUSLY with the invalidation. The
  invalidation only clears the cache — it does not change what the
  origin serves.

- **`list-invalidations` does not show per-edge-location status.**
  The `InvalidationStatus` is a global aggregate. `Completed` means
  all edge locations have processed the invalidation. There is no
  per-region or per-edge status. For debugging "some users still see
  old content," check browser cache, DNS TTL, and origin health —
  not per-edge invalidation status.

- **Multipart invalidation batches have a 3,000-path hard limit per
  request.** `create-invalidation` accepts up to 3,000 paths per API
  call (including wildcards). For more than 3,000 paths, use
  multiple `create-invalidation` calls, or replace with a single
  `/*` invalidation.

- **Lambda@Edge and CloudFront Functions are not invalidated.**
  Function code updates propagate independently of cache
  invalidation. If you updated a Lambda@Edge function, the function
  update can take up to 5 minutes (CloudFront Functions) or up to
  15 minutes (Lambda@Edge) to propagate to all edge locations.
  Invalidation does not speed this up.

- **S3 origin vs custom origin invalidation behavior is identical.**
  The origin type does not affect invalidation. CloudFront tracks
  cached objects by URL regardless of origin type. The invalidation
  path pattern matches the URL path as seen by the viewer.


---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **CloudFront continuous deployment (2022 GA, 2024-2026 hardening):**
  Traffic-splitting between a primary and staging distribution.
  Invalidation on the primary does NOT affect staging. Staging has
  its own distribution ID and edge cache. Test changes on staging,
  then promote to primary via `update-distribution`.

- **CloudFront KeyValueStore (2024):** Edge key-value store for
  CloudFront Functions. Updates to KeyValueStore propagate
  independently of cache invalidation. Do not use invalidation to
  force KeyValueStore updates — use `update-key-value-store` directly.

- **CloudFront response headers policies (2024-2025):** Managed
  response headers policies now include `Cache-Control` overrides.
  These are applied at the edge independently of origin headers.
  Verify the response headers policy before assuming the origin's
  `Cache-Control` is being respected.

- **CloudFront origin access control (OAC, 2023-2024):** Replaces
  origin access identity (OAI). Does not affect invalidation
  behavior — invalidation operates on edge cache, not origin access.

- **CloudFront Metrics (2025):** Enhanced real-time metrics now
  include per-status-code cache hit/miss rates. Use these to verify
  that an invalidation had the expected effect (cache miss rate
  spikes after invalidation, then normalizes as the new content is
  cached).

- **CloudFront Functions vs Lambda@Edge propagation (2024-2026):**
  CloudFront Functions updates propagate in ~5 minutes; Lambda@Edge
  updates propagate in ~15 minutes. These are independent of cache
  invalidation. If a function change is not reflected, check
  function propagation status, not invalidation status.

- **S3 Object Lambda with CloudFront (2024):** When using S3 Object
  Lambda as a CloudFront origin, invalidation clears the edge cache
  but the Object Lambda transformation is applied on each origin
  fetch. Verify the transformation is correct before invalidating.
