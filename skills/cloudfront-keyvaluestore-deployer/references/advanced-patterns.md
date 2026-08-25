# Advanced Patterns (load on demand) — CloudFront KeyValueStore Deployer

Deep-dive material moved verbatim from SKILL.md: the KVS read-write asymmetry and etag concurrency heuristic, plus the recent-features notes.


---

## Expert heuristic: KVS read-write asymmetry and etag concurrency (moved from SKILL.md)

KVS has a fundamental read-write asymmetry that a baseline model
conflates. This heuristic separates the two planes.

```text
WRITE PATH (operator-side, via AWS API):
  aws cloudfront-keyvaluestore put-key
    --kvs-arn <arn> --key <key> --value <value> --if-match <etag>
    → writes to the KVS data plane
    → etag increments
    → CloudFront propagates the update to all edge PoPs (seconds to minutes)

READ PATH (function-side, at the edge):
  cf.openKvs().get('<key>')
    → reads from the local edge copy of the KVS
    → READ-ONLY — no put/delete from function code
    → may return stale data during propagation window
```

**Key implication:** the write path is an AWS API call (CLI, SDK, IaC).
The read path is a JavaScript runtime call inside the function. They
are completely different interfaces. A common mistake is to try to
write KVS data from inside a function (impossible) or to try to read
KVS data via CLI `get-key` in a function (wrong API surface).

**Operational pattern for A/B test rotation:** Operator updates the
KVS via CLI (`put-key --key "ab-cohort" --value "variant-b"`), CloudFront
propagates to edge locations, functions read the new value on subsequent
requests — no function code change or redeployment needed. The KVS is
the configuration; the function is the logic.

**etag-based optimistic concurrency:** Every KVS mutation requires the
current etag (`--if-match`). A stale etag returns `PreconditionFailed`.
Scripts that batch-update keys must re-fetch the etag before each write
or chain it from the previous response:

```text
put-key --if-match E1  → SUCCESS, new etag = E2
put-key --if-match E1  → FAIL: PreconditionFailed
put-key --if-match E2  → SUCCESS, new etag = E3
```

**Propagation window:** KVS is eventually consistent across ~600+ edge
locations. Typical convergence: 5-15 seconds for major PoPs, 30-60
seconds for long-tail, up to 5 minutes worst-case. During the window,
functions at different PoPs may read different values. For A/B testing
and feature flags, this is tolerable. For security-critical IP
blocklists, use AWS WAF IP sets for near-instant propagation.


---

## Step 9 — Recent features (moved from SKILL.md)

- **CloudFront KeyValueStore GA (late 2023):** Managed key-value store
  for CloudFront Functions, enabling edge-side data lookup without
  origin calls or function redeployment.
- **cloudfront-js-2.0 runtime with KVS API (2023-2024):** Introduced
  `cf.openKvs()` for reading KVS inside functions. REQUIRED for KVS
  access; `cloudfront-js-1.0` does not support it.
- **KVS in CloudFormation and Terraform (2024-2025):** Full IaC support
  via `AWS::CloudFront::KeyValueStore` and `aws_cloudfront_key_value_store`.
- **CloudFront Functions test API for KVS (2024-2025):** `test-function`
  now supports KVS-linked functions for pre-publish testing.
- **KVS metrics in CloudWatch (2024-2025):** `KvsSize`, `KvsItemCount`,
  and function-level KVS read latency.
