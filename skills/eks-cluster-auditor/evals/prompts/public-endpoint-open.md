# Eval prompt: public-endpoint-open

Audit the following EKS cluster configuration for security exposure.
Latest available EKS version: 1.32. Emit the standard VERDICT block
(CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster name: public-endpoint-open
Cluster config (describe-cluster output):

```json
{
  "cluster": {
    "name": "public-endpoint-open",
    "version": "1.28",
    "status": "ACTIVE",
    "resourcesVpcConfig": {
      "endpointPublicAccess": true,
      "endpointPrivateAccess": false,
      "publicAccessCidrs": ["0.0.0.0/0"]
    },
    "logging": {
      "clusterLogging": [
        {"types": ["api","audit","authenticator","controllerManager","scheduler"], "enabled": false}
      ]
    }
  }
}
```

aws-auth ConfigMap mapRoles:

```json
[
  {
    "rolearn": "arn:aws:iam::111111111111:role/eks-node-role",
    "username": "system:node:{{EC2PrivateDNSName}}",
    "groups": ["system:bootstrappers", "system:nodes"]
  },
  {
    "rolearn": "arn:aws:iam::111111111111:role/eks-admin-role",
    "username": "admin",
    "groups": ["system:masters"]
  }
]
```

Node security groups:

```json
[
  {
    "groupId": "sg-node-001",
    "groupName": "eks-node-sg",
    "ipPermissions": [
      {"fromPort": 10250, "toPort": 10250, "ipProtocol": "tcp", "ipRanges": [{"cidrIp": "0.0.0.0/0"}]}
    ]
  }
]
```
