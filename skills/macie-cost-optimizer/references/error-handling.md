# Error handling — macie-cost-optimizer

Data-gate failure modes and disagreement handling moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Data-quality short-circuits (pre-flight data gate)

| Condition | Effect on optimization |
|---|---|
| Cost Explorer Macie line items absent | **NEED_MORE_INFO**. Macie may not be enabled, or filter is wrong. Verify `get-macie-account`. |
| Macie window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| `list-classification-jobs` returns empty AND automated discovery disabled | **NEED_MORE_INFO**. No coverage to optimize. |
| `jobStatus: RUNNING` for > 24 hours on a large bucket | Job is in flight; wait for completion before re-baselining. |
| `lastRunTime` > 30 days ago on a recurring job | Stale config; job may have errored. Verify `lastRunError`. |
| IAM denies `macie2:GetClassificationScope` | Surface as BLOCKED; cannot evaluate excludes without scope access. |

When Cost Explorer and Macie job stats disagree, the Macie job stats
(`bytesProcessed`, `objectsProcessed`) are the ground truth — Cost
Explorer reflects invoiced spend which may lag by up to 24 hours.
