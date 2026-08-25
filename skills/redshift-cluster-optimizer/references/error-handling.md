# Error Handling — Redshift Cluster Optimizer

Failure modes for CLI calls and data sources, moved verbatim from
SKILL.md.

## Error handling — CLI and data-source failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-clusters` returns empty | `len(Clusters) == 0` | No clusters to optimise. ALREADY_OPTIMAL for fleet. |
| CloudWatch CPUUtilization returns empty | `len(Datapoints) == 0` | Cluster may be paused/stopped. Check ClusterStatus. |
| `resize-cluster` returns InvalidClusterState | Resize in progress or incompatible | Wait for current operation to complete. |
| `purchase-reserved-node-offering` fails | Offering ID stale | Re-query for a fresh offering-id. |
| Serverless workgroup not found | `ResourceNotFoundException` | Check workgroup name and region. |
| Concurrency Scaling metrics absent | CS never triggered | CS is enabled but unused — no cost impact. |
| Cluster in `modifying` state | ClusterStatus | Wait for completion before recommending changes. |
| VACUUM running | `STV_TBL_PERM` shows active vacuum | Do not recommend concurrent VACUUMs. |
