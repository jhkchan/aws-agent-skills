# Eval prompt: upgrade-addon-vpc-cni-bridge-version-ready

Plan the following VPC-CNI pre-upgrade (to a bridge version) and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, ROLLBACK, NOTES).

Operation: upgrade-addon
Cluster: prod-cluster-01
Add-on: vpc-cni
Current add-on version: v1.15.5-eksbuild.1
Target add-on version: v1.17.3-eksbuild.2 (bridge version)
Reason: pre-upgrade to Kubernetes 1.29
Current Kubernetes: 1.28
Target Kubernetes: 1.29

```json
{
  "AddonMetadata": {
    "addonName": "vpc-cni",
    "addonVersion": "v1.15.5-eksbuild.1",
    "status": "ACTIVE",
    "clusterName": "prod-cluster-01"
  },
  "AddonVersionCompatibility": {
    "v1.17.3-eksbuild.2": {"compatWith_1_28": true, "compatWith_1_29": true},
    "v1.19.1-eksbuild.1": {"compatWith_1_28": false, "compatWith_1_29": true}
  },
  "ConfigurationValuesBackup": "kubectl get daemonset aws-node -n kube-system -o yaml > /tmp/vpc-cni-preupgrade-20260807.yaml (done)"
}
```
