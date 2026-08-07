# Eval prompt: upgrade-nodegroup-pdb-blocks-drain-blocked

Plan the following EKS managed node group upgrade and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, ROLLBACK, NOTES).

Operation: upgrade-nodegroup
Cluster: prod-cluster-01
Node group: prod-ng-1
Current node version: 1.28
Target node version: 1.29
Control plane version: 1.29 (already upgraded)

```json
{
  "NodeGroupMetadata": {
    "nodegroupName": "prod-ng-1",
    "status": "ACTIVE",
    "version": "1.28",
    "clusterName": "prod-cluster-01",
    "instanceTypes": ["m5.large"],
    "subnets": ["subnet-aaa", "subnet-bbb", "subnet-ccc"],
    "scalingConfig": {"minSize": 3, "desiredSize": 5, "maxSize": 10},
    "updateConfig": {"maxUnavailable": 1, "maxSurge": 0}
  },
  "ClusterVersion": "1.29",
  "SubnetIPs": {
    "subnet-aaa": 47,
    "subnet-bbb": 51,
    "subnet-ccc": 38
  },
  "PodDisruptionBudgets": [
    {"namespace": "payments", "name": "payments-api-pdb", "minAvailable": 4, "allowedDisruptions": 0},
    {"namespace": "kube-system", "name": "coredns-pdb", "minAvailable": 1, "allowedDisruptions": 1}
  ],
  "PaymentsApiDeployment": {
    "replicas": 4,
    "spread": "across 4 nodes in prod-ng-1"
  }
}
```
