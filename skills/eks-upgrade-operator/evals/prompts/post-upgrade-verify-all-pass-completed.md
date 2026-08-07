# Eval prompt: post-upgrade-verify-all-pass-completed

Verify the following completed EKS cluster upgrade and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, ROLLBACK, NOTES) in the post-verification COMPLETED form.

Operation: post-upgrade-verify
Cluster: prod-cluster-01
Previous version: 1.28
Target version: 1.29

```json
{
  "ClusterDescribe": {
    "version": "1.29",
    "status": "ACTIVE"
  },
  "Nodes": {
    "total": 10,
    "allReady": true,
    "allAtVersion": "v1.29.3-eks-..."
  },
  "FailedPods": "No resources found.",
  "UnavailableAPIServices": "none (kubectl get apiservices | grep False is empty)",
  "EksAddons": [
    {"name": "vpc-cni", "version": "v1.18.4-eksbuild.1", "status": "ACTIVE", "compatWith_1_29": true},
    {"name": "coredns", "version": "v1.11.3-eksbuild.3", "status": "ACTIVE", "compatWith_1_29": true},
    {"name": "kube-proxy", "version": "v1.29.3-minimal-1", "status": "ACTIVE", "compatWith_1_29": true}
  ],
  "CanaryRollout": "deployment \"canary\" successfully rolled out",
  "ApplicationMetrics": {
    "errorRate": "0.02%",
    "baseline": "0.02%",
    "spikeDetected": false
  }
}
```
