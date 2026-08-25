# Error Handling (load on demand) — CloudFront Invalidation Operator

Error reference moved verbatim from SKILL.md: the invalidation failure-mode table used during diagnose-invalidation.


---

## Invalidation failure-mode table (moved from SKILL.md)

**Invalidation failure-mode table (use during diagnose-invalidation):**

| Symptom | Root cause | Fix |
|---|---|---|
| `create-invalidation` returns `AccessDenied` | Caller lacks `cloudfront:CreateInvalidation` on the distribution ARN | Add the permission to the caller's IAM policy |
| `create-invalidation` returns `InvalidArgument: Your request has a path that contains an invalid character` | Path contains characters not allowed (spaces, `?`, `#`, or wildcard mid-segment) | Fix the path syntax: start with `/`, URL-encode special chars, wildcard only at segment end |
| `create-invalidation` returns `TooManyInvalidationsInProgress` | More than 15 concurrent InProgress invalidations for the distribution | Wait for existing invalidations to Complete, or consolidate into fewer batches with wildcards |
| `create-invalidation` returns `CNAMEAlreadyExists` | Unrelated to invalidation — distribution config conflict | This is a distribution-update error, not an invalidation error |
| Invalid path count exceeds 3,000 | Hard limit per API call | Split into multiple `create-invalidation` calls, or use `/*` |
| `InvalidationStatus: InProgress` for > 15 minutes | Large wildcard invalidation or edge propagation delay | Wait; if > 30 minutes, check CloudFront service health |
| Invalidation Completed but users still see old content | Browser cache, DNS TTL, or CDN in front of CloudFront | Check `Cache-Control` headers, DNS resolution, intermediate CDN caches |
| Invalidation returns existing invalidation (no new one created) | `CallerReference` collision with a previous invalidation | Generate a new unique `CallerReference` (UUID or timestamp) |
| `create-invalidation` on staging distribution fails | Staging distribution ID is different from the primary; caller may lack permissions on the staging distribution | Use the staging distribution ID from `get-continuous-deployment-policy`; ensure IAM policy covers both |
| Cost is higher than expected | Individual paths counted instead of wildcards; monthly cumulative exceeds 1,000 | Use `/*` or directory wildcards; monitor monthly path count |
