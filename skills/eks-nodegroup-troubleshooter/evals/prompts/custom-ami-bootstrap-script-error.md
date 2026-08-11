# Eval prompt: custom-ami-bootstrap-script-error

Diagnose the EKS node group issue for the following cluster. Walk the
node-state-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: a new node group `prod-ng-custom` was created with a custom
AMI. EC2 instances launch (visible in the ASG and EC2 console) but
never appear in `kubectl get nodes`. The ASG marks them unhealthy
after the health check grace period and replaces them, creating a
cycle.

```text
ClusterName: prod-cluster
NodeGroupName: prod-ng-custom
AmiType: CUSTOM_TEMPLATE
LaunchTemplate:
  ImageId: ami-0abc123def456 (custom AMI)
  UserData: |
    #!/bin/bash
    /etc/eks/bootstrap.sh prod-cluster \
      --apiserver-endpoint https://10.0.0.1 \
      --b64-cluster-ca LS0tLS1CRUdJTi
    /opt/aws/bin/cfn-signal

Cluster API server endpoint:
  https://A1B2C3D4...gr7.us-east-1.eks.amazonaws.com
  (The user-data has 10.0.0.1 which is a private IP, NOT the
  EKS API server endpoint)

ASG Activity:
  StatusCode: Failed
  StatusMessage: "Instance became unhealthy"

aws ec2 get-console-output (instance i-0xyz):
  + /etc/eks/bootstrap.sh prod-cluster --apiserver-endpoint https://10.0.0.1
  ...
  [error] Failed to connect to API server https://10.0.0.1:
    dial tcp 10.0.0.1:443: connect: connection refused
  [error] kubelet failed to start: unable to load bootstrap
    kubeconfig

kubectl get nodes:
  (empty — no nodes from this node group registered)
```

The instances are launching successfully but the bootstrap script is
connecting to the wrong API server endpoint. The actual EKS endpoint
is `https://A1B2C3D4...gr7.us-east-1.eks.amazonaws.com` but the
user-data specifies `https://10.0.0.1`.
