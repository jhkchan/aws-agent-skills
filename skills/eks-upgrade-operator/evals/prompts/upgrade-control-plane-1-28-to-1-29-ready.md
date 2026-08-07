# Eval prompt: upgrade-control-plane-1-28-to-1-29-ready

Plan the following EKS control plane upgrade and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, ROLLBACK, NOTES).

Operation: upgrade-control-plane
Cluster: prod-cluster-01
Current version: 1.28
Target version: 1.29
Region: us-east-1

```json
{
  "ClusterMetadata": {
    "name": "prod-cluster-01",
    "status": "ACTIVE",
    "version": "1.28",
    "logging": {
      "clusterLogging": [
        {"types": ["api","audit","authenticator","controllerManager","scheduler"], "enabled": true}
      ]
    }
  },
  "InProgressUpdates": "none",
  "EksAddons": [
    {"name": "vpc-cni", "version": "v1.17.3-eksbuild.2", "status": "ACTIVE",
     "compatWith_1_28": true, "compatWith_1_29": true},
    {"name": "coredns", "version": "v1.11.1-eksbuild.4", "status": "ACTIVE",
     "compatWith_1_28": true, "compatWith_1_29": true},
    {"name": "kube-proxy", "version": "v1.28.7-minimal-1", "status": "ACTIVE",
     "compatWith_1_28": true, "compatWith_1_29": true}
  ],
  "ManagedNodeGroups": [
    {"name": "prod-ng-1", "version": "1.28", "status": "ACTIVE"},
    {"name": "prod-ng-2", "version": "1.28", "status": "ACTIVE"}
  ],
  "NodeVersions": "all 10 nodes Ready, all at v1.28.x",
  "KubentScan_1_29": "no deprecated APIs in use (no FlowSchema v1beta1 found)"
}
```
