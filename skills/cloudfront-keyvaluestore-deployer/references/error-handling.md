# Error Handling (load on demand) — CloudFront KeyValueStore Deployer

Error handling moved verbatim from SKILL.md: the KVS/Functions failure catalog.


---

## Error handling (moved from SKILL.md)

- **`SizeLimitExceeded` on `put-key`:** Total store exceeds 1 MB. Check
  `describe-key-value-store --query 'Size'`. Remove unused keys or
  abbreviate content. Split across multiple KVS stores.
- **`PreconditionFailed` on mutation:** Stale etag. Re-fetch via
  `describe-key-value-store` and retry. Chain etags for batch scripts.
- **Function reads `undefined`:** Key name mismatch (case-sensitive).
  Verify the key string via `list-keys` matches `kvs.get()` exactly.
- **Function fails silently at the edge:** Runtime likely
  `cloudfront-js-1.0`. Verify via `describe-function`. Update to
  `cloudfront-js-2.0` and republish.
- **Function not executing on distribution:** Function in
  `DEVELOPMENT` stage. Call `publish-function`. Verify the
  distribution's `FunctionAssociations` includes the function ARN.
