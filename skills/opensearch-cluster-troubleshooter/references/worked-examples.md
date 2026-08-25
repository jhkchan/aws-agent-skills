# Worked examples — opensearch-cluster-troubleshooter

Secondary output examples moved verbatim from SKILL.md (load on demand). The primary worked example (flood-stage disk block) remains in SKILL.md.

## Malformed input — INSUFFICIENT_DATA output

```text
TARGET: <domain-name or unknown>
VERDICT: INSUFFICIENT_DATA
ROOT_CAUSE: UNKNOWN
REASON: Input is missing required context — at minimum a symptom
  description (the error string, observed cluster status, or an
  alarm name) and the DomainName (with region for live diagnosis).
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact error string
  or observed symptom, (2) the DomainName and region, and (3) for
  live diagnosis, the most recent `_cluster/health?pretty` output
  and the CloudWatch `ClusterIndexWritesBlocked`, `JVMHeapPressure`,
  and `ClusterStatus.red` metrics over the last 30 minutes.
```
