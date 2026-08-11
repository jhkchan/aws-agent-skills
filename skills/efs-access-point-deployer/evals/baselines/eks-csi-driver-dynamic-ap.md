# Baseline (no-skill) — eks-csi-driver-dynamic-ap

> This is the response a model produces **without** the skill definition.
> It creates the StorageClass with dynamic provisioning but omits
> `elasticfilesystem:ClientRootAccess` from the IRSA role policy — so
> the CSI driver mounts successfully but cannot enforce the access
> point's directory permissions, silently breaking per-pod isolation.
> Generated for with-skill-vs-baseline comparison.

---

To set up EFS with the CSI driver:

1. Create the IRSA role policy (allowing CSI driver to manage
   access points):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "elasticfilesystem:CreateAccessPoint",
      "elasticfilesystem:DeleteAccessPoint",
      "elasticfilesystem:DescribeAccessPoints",
      "elasticfilesystem:DescribeFileSystems",
      "elasticfilesystem:ClientMount",
      "elasticfilesystem:ClientWrite"
    ],
    "Resource": "*"
  }]
}
```

2. Apply the StorageClass:
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-ccccdddddddd
  directoryPerms: "700"
  gidRangeStart: "1000"
  gidRangeEnd: "2000"
```

3. Create a PVC and verify the CSI driver provisions a dynamic
   access point per PVC.
