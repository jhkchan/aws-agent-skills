# Eval prompt: upgrade-control-plane-skip-version-blocked

Plan the following EKS control plane upgrade attempt and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, ROLLBACK, NOTES).

Operation: upgrade-control-plane
Cluster: prod-cluster-01
Current version: 1.27
Target version: 1.29
Region: us-east-1

```json
{
  "ClusterMetadata": {
    "name": "prod-cluster-01",
    "status": "ACTIVE",
    "version": "1.27"
  },
  "AvailableVersions": ["1.27", "1.28", "1.29", "1.30", "1.31"]
}
```
