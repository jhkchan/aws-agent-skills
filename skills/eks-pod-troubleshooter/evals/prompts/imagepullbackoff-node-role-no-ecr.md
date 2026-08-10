# Eval prompt: imagepullbackoff-node-role-no-ecr

Diagnose the following EKS pod failure. Walk the ImagePullBackOff
diagnostic tree and emit the standard VERDICT block (INCIDENT, VERDICT,
ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A Kubernetes pod on an EKS cluster is in `ImagePullBackOff`.
Namespace: `production`. Pod: `worker-7c8d9e-x2k3l`.

## Known facts

- `kubectl get pod worker-7c8d9e-x2k3l -n production -o wide` shows:
  STATUS=`ImagePullBackOff`.
- The pod image is
  `111111111111.dkr.ecr.us-east-1.amazonaws.com/app:v1`.
- `kubectl describe pod worker-7c8d9e-x2k3l -n production` Events:
  ```
  Warning  Failed   kubelet  Failed to pull image
  "111111111111.dkr.ecr.us-east-1.amazonaws.com/app:v1":
  rpc error: code = Unknown desc = Error response from daemon: Head
  "https://111111111111.dkr.ecr.us-east-1.amazonaws.com/v2/app/manifests/v1":
  unauthorized: Not Authorized
  ```
- The pod is scheduled on node `ip-10-0-2-20.ec2.internal`, instance
  ID `i-0abc123def456`. The instance's IAM instance profile role is
  `eksctl-prod-cluster-ng-NodeInstanceRole-ABC`.
- `aws ecr describe-images --repository-name app --image-ids
  imageTag=v1` confirms the image exists.
- `aws iam list-attached-role-policies --role-name
  eksctl-prod-cluster-ng-NodeInstanceRole-ABC` shows:
  - `AmazonSSMManagedInstanceCore`
  - `AmazonEKS_CNI_Policy`
- `aws iam simulate-principal-policy --policy-source-arn
  arn:aws:iam::111111111111:role/eksctl-prod-cluster-ng-NodeInstanceRole-ABC
  --action-names ecr:BatchGetImage` returns `implicitDeny`.

## Symptom

The pod never reaches `ContainerCreating` — it stays in
`ImagePullBackOff` indefinitely.
