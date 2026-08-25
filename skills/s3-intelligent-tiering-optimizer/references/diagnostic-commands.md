# Diagnostic commands - S3 Intelligent-Tiering Optimizer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight: bucket metadata gate

Run before classification. Misclassifying these produces false positives.

**Pagination:** `list-bucket-intelligent-tiering-configurations`
paginates at 100 configurations/page. For most buckets there is only one
configuration (named `Config` by default). `list-objects-v2` paginates
at 1,000 keys/page — for large buckets, do NOT iterate live; pull Storage
Lens aggregate metrics instead.

**Live-account pre-flight (skip if offline audit):**
1. `aws s3api list-bucket-intelligent-tiering-configurations --bucket
   <name>` — capture existing configurations (Id, Status, Tierings,
   Filter).
2. `aws s3api get-bucket-lifecycle-configuration --bucket <name>` —
   capture any lifecycle rules that overlap prefixes targeted for
   Intelligent-Tiering.
3. `aws s3control get-storage-lens-configuration --config-id default`
   — capture object-size distribution, access-pattern trend, average
   object age.
4. `aws s3api get-object-lock-configuration --bucket <name>` — if
   Object Lock is enabled, restrict archive-tier recommendations for
   compliance workloads.
5. `aws s3api list-objects-v2 --bucket <name> --page-size 1000
   --max-items 100` — sample the smallest 100 keys for the
   small-object heuristic (alternative: read the ObjectSizeDistribution
   from Storage Lens).
6. For directory buckets: bucket name suffix `--x-s3` signals no
   Intelligent-Tiering support; skip the configuration dimensions.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Bucket configuration is not
valid JSON or is missing required fields — cannot classify.` and
`REMEDIATION: Re-fetch with aws s3api
list-bucket-intelligent-tiering-configurations --bucket <name> --output
json and re-audit.`

| Bucket attribute | Effect on audit |
|---|---|
| Bucket is a directory bucket (name suffix `--x-s3`) | Intelligent-Tiering NOT supported. Verdict: ALREADY_OPTIMAL for ML/AI workloads. |
| Bucket has S3 Tables prefixes (Apache Iceberg) | Do not propose Intelligent-Tiering on table-data prefixes; tables manage their own lifecycle. Surface as a finding only. |
| Object Lock `Enabled` COMPLIANCE mode | Restrict archive-tier recommendations for compliance workloads requiring periodic retrieval; Frequent Access only. |
| Existing IntelligentTieringConfiguration with Status `Enabled` | Compare actual tier distribution from Storage Lens before re-recommending. |
| Existing lifecycle rule with overlapping prefix | Surface the overlap; pick one system per prefix. |
| Cross-Region Replication destination | Intelligent-Tiering applies to the destination independently. Run the tree on both sides. |
| Requester-pays bucket | Monitoring fee bills the bucket owner; retrieval bills the requester. Note in savings estimate. |

