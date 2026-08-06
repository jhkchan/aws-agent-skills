# Eval prompt: clean-hardened-cluster

Audit the following EKS cluster configuration for security exposure.
Latest available EKS version: 1.32. Emit the standard VERDICT block
(CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster name: clean-hardened-cluster
Cluster config (describe-cluster output):

```json
{
  "cluster": {
    "name": "clean-hardened-cluster",
    "version": "1.31",
    "status": "ACTIVE",
    "resourcesVpcConfig": {
      "endpointPublicAccess": false,
      "endpointPrivateAccess": true,
      "publicAccessCidrs": []
    },
    "logging": {
      "clusterLogging": [
        {"types": ["api","audit","authenticator","controllerManager","scheduler"], "enabled": true}
      ]
    }
  }
}
```

aws-auth ConfigMap mapRoles:

```json
[
  {
    "rolearn": "arn:aws:iam::111111111111:role/eks-admin-role",
    "username": "admin",
    "groups": ["system:masters"]
  },
  {
    "rolearn": "arn:aws:iam::111111111111:role/eks-node-role",
    "username": "system:node:{{EC2PrivateDNSName}}",
    "groups": ["system:bootstrappers", "system:nodes"]
  }
]
```

Node security groups:

```json
[
  {
    "groupId": "sg-node-006",
    "groupName": "eks-node-sg",
    "ipPermissions": [
      {"fromPort": 10250, "toPort": 10250, "ipProtocol": "tcp", "ipRanges": [{"cidrIp": "10.0.0.0/16"}]}
    ]
  }
]
```
