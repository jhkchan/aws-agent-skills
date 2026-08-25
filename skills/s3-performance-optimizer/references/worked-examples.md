# Worked Examples — S3 Performance Optimizer

Full output-block examples moved from SKILL.md. Load on demand.

## Worked example: malformed input verdict (UNKNOWN)

```text
TARGET: <bucket or unknown>
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Input is missing required context — at minimum a BucketName
  and a workload description (PUT vs GET, object size profile, request
  rate, client geography, target latency/throughput). CloudWatch S3
  metrics and Storage Lens excerpts are required for high-confidence
  layer identification.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt for: (1) BucketName and region; (2) workload
  type (PUT-heavy, GET-heavy, mixed); (3) object size profile;
  (4) request rate; (5) client geography; (6) target latency or
  throughput; (7) CloudWatch request metrics for the last hour.
```

