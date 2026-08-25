# Provisioning CLI Commands — EFS Access Points Deployer

Full copy-pasteable CLI command sequence for the 9-step provisioning
procedure. Variables to substitute: `<FS_ID>`, `<AP_ID>`,
`<AP_NAME>`, `<ACCOUNT_ID>`, `<REGION>`, `<UID>`, `<GID>`,
`<SUBNET_ID>`, `<MT_SG_ID>`, `<CLIENT_SG_ID>`, `<VPC_ID>`,
`<CLUSTER>`, `<TASK_ROLE_ARN>`, `<FN_NAME>`, `<IRSA_ROLE_ARN>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)
echo "Account: $ACCOUNT_ID  Region: $REGION"

# File system exists and meets baseline
aws efs describe-file-systems --file-system-id <FS_ID> \
  --query 'FileSystems[0].[Encrypted,ThroughputMode,ProvisionedThroughputInMibps]'

aws efs describe-lifecycle-configuration --file-system-id <FS_ID>

# Mount targets in every compute AZ
aws efs describe-mount-targets --file-system-id <FS_ID> \
  --query 'MountTargets[].[AvailabilityZoneName,SubnetId,MountTargetId]' --output table

# amazon-efs-utils installed on the target host (EC2/on-prem)
which mount.efs || echo "MISSING: install amazon-efs-utils"

# EFS CSI driver installed on EKS
kubectl get pods -n kube-system -l app=efs-csi-controller 2>/dev/null \
  || echo "MISSING: install EFS CSI driver add-on"
```

## Step 1: File-system baseline

Confirm encryption at rest, throughput mode, and lifecycle policy. See
`efs-file-system-deployer` for the full baseline procedure.

```bash
aws efs describe-file-systems --file-system-id <FS_ID>
aws efs describe-lifecycle-configuration --file-system-id <FS_ID>
```

## Step 2: Verify mount targets in every compute AZ

```bash
# List mount targets
aws efs describe-mount-targets --file-system-id <FS_ID>

# List compute subnets and their AZs
aws ec2 describe-subnets --filters Name=vpc-id,Values=<VPC_ID> \
  --query 'Subnets[].[AvailabilityZone,SubnetId]' --output table

# Create a mount target in a missing AZ
aws efs create-mount-target \
  --file-system-id <FS_ID> \
  --subnet-id <SUBNET_ID> \
  --security-groups <MT_SG_ID>
```

## Step 3: Install / verify amazon-efs-utils

```bash
# Amazon Linux 2023
sudo dnf install -y amazon-efs-utils

# Ubuntu
sudo apt-get install -y amazon-efs-utils

# Verify
which mount.efs
mount -t efs

# EKS: install the CSI driver add-on
aws eks create-addon --cluster-name <CLUSTER> \
  --addon-name aws-efs-csi-driver \
  --service-account-role-arn <IRSA_ROLE_ARN>
```

## Step 4: Create the access point

```bash
aws efs create-access-point \
  --name <AP_NAME> \
  --file-system-id <FS_ID> \
  --posix-user Uid=<UID>,Gid=<GID>,SecondaryGids=<GID1>,<GID2> \
  --root-directory \
    Path=/data/team-a,CreationInfo={OwnerUid=<UID>,OwnerGid=<GID>,Permissions=0750}

# Capture the access-point ID
AP_ID=$(aws efs describe-access-points --file-system-id <FS_ID> \
  --query 'AccessPoints[?Name==`<AP_NAME>`].AccessPointId' --output text)
echo "Access point ID: $AP_ID"
```

## Step 5: Attach file-system policy

```bash
aws efs put-file-system-policy --file-system-id <FS_ID> \
  --policy file://fs-policy.json
```

See `references/file-system-policy-examples.md` section 1 for the
policy document with the access-point-only `Deny`.

## Step 6: Mount via the access point with TLS

```bash
# EC2 / on-prem
sudo mkdir -p /mnt/efs/team-a
sudo mount -t efs -o tls,accesspoint=<AP_ID> <FS_ID>:/ /mnt/efs/team-a

# fstab equivalent
echo "<FS_ID>:/ /mnt/efs/team-a efs _netdev,tls,accesspoint=<AP_ID> 0 0" | sudo tee -a /etc/fstab

# Verify TLS is active
mount | grep efs
sudo ss -tnp | grep 2049  # stunnel process should be visible
```

## Step 7a: ECS task definition with EFS volume

```bash
# volumes.json
cat > volumes.json <<'EOF'
[{
  "name": "efs-team-a",
  "efsVolumeConfiguration": {
    "fileSystemId": "<FS_ID>",
    "transitEncryption": "ENABLED",
    "accessPointId": "<AP_ID>",
    "iam": "ENABLED"
  }
}]
EOF

aws ecs register-task-definition \
  --family <FAMILY> \
  --task-role-arn <TASK_ROLE_ARN> \
  --execution-role-arn <EXEC_ROLE_ARN> \
  --container-definitions file://containers.json \
  --volumes file://volumes.json \
  --requires-compatibilities EC2 FARGATE \
  --network-mode awsvpc
```

## Step 7b: EKS storage class with EFS CSI driver

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: <FS_ID>
  directoryPerms: "700"
  gidRangeStart: "1000"
  gidRangeEnd: "2000"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-pvc
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```

Apply with `kubectl apply -f efs-sc.yaml`. Verify the PVC binds and
the CSI driver creates a corresponding access point:

```bash
kubectl get pvc efs-pvc
kubectl get pv
aws efs describe-access-points --file-system-id <FS_ID> \
  --query 'AccessPoints[].{Name:Name,Id:AccessPointId}'
```

## Step 8: Lambda function with EFS

```bash
aws lambda update-function-configuration \
  --function-name <FN_NAME> \
  --vpc-config SubnetIds=<SUBNET1>,<SUBNET2>,SecurityGroupIds=<SG_ID> \
  --file-system-configs \
    Arn=arn:aws:elasticfilesystem:<REGION>:<ACCOUNT_ID>:access-point/<AP_ID>,LocalMountPath=/mnt/efs

# Verify the function's VPC and file-system config
aws lambda get-function-configuration \
  --function-name <FN_NAME> \
  --query '[VpcConfig.SubnetIds, fileSystemConfigs]'
```

## Step 9: Verification

```bash
aws efs describe-access-points --access-point-id <AP_ID>
aws efs describe-file-system-policy --file-system-id <FS_ID>
aws efs describe-mount-targets --file-system-id <FS_ID>
aws efs describe-lifecycle-configuration --file-system-id <FS_ID>

# (ECS) Confirm the task mounts the EFS volume
aws ecs describe-tasks --cluster <CLUSTER> --tasks <TASK_ARN> \
  --query 'tasks[0].volumes'

# (EKS) Confirm the PVC bound
kubectl get pvc -n <NAMESPACE>

# (Lambda) Confirm the file-system config
aws lambda get-function-configuration --function-name <FN_NAME> \
  --query 'fileSystemConfigs'
```

---

## Step 9 — Verification command listing (moved from SKILL.md)

```bash
aws efs describe-access-points --access-point-id <AP_ID>
aws efs describe-file-system-policy --file-system-id <FS_ID>
aws efs describe-mount-targets --file-system-id <FS_ID>
aws efs describe-lifecycle-configuration --file-system-id <FS_ID>
# (ECS) confirm the task mounts:
aws ecs describe-tasks --cluster <CLUSTER> --tasks <TASK_ARN> \
  --query 'tasks[0].volumes'
# (EKS) confirm the PVC bound:
kubectl get pvc -n <NAMESPACE>
# (Lambda) confirm the file-system config:
aws lambda get-function-configuration --function-name <FN_NAME> \
  --query 'fileSystemConfigs'
```

