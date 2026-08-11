# Eval prompt: nodegroup-ami-version-mismatch

Diagnose the EKS node group issue for the following cluster. Walk the
node-state-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: after upgrading the EKS control plane to 1.30, 3 of 5 nodes
in the node group are NotReady. Pods are being evicted. The node group
AMI version has not been updated.

```text
ClusterName: prod-cluster
NodeGroupName: prod-ng-1
ClusterKubernetesVersion: "1.30"
NodeGroupAmiType: AL2_x86_64
NodeGroupVersion: "1.28"
NodeGroupReleaseVersion: "1.28.7-20240625"

kubectl get nodes:
  ip-10-0-10-10   Ready     <none>   120d   v1.28.7-eks-ba74326
  ip-10-0-10-11   Ready     <none>   120d   v1.28.7-eks-ba74326
  ip-10-0-10-12   NotReady  <none>   5m     v1.28.7-eks-ba74326
  ip-10-0-11-10   NotReady  <none>   5m     v1.28.7-eks-ba74326
  ip-10-0-11-11   NotReady  <none>   5m     v1.28.7-eks-ba74326

kubectl describe node ip-10-0-10-12:
  Conditions:
    Ready: False  Reason: KubeletNotReady
    Message: container runtime network not ready
```

The kubelet version (v1.28.7) is two minor versions behind the API
server (v1.30). EKS supports at most one minor version skew.
