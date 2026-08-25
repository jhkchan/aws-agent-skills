# Provisioning CLI Commands — EKS Add-On Deployer

Full copy-pasteable CLI command sequence for provisioning EKS add-ons:
core networking, storage, observability, IRSA, Pod Identity, and
conflict resolution. Variables to substitute: `<cluster-name>`,
`<k8s-version>`, `<account-id>`, `<addon-name>`, `<addon-version>`.

## Step 0: Prerequisites check

```bash
# Confirm cluster exists and is ACTIVE
aws eks describe-cluster \
  --name <cluster-name> \
  --query 'cluster.{Name:name,Status:status,Version:version}'

# List currently installed add-ons
aws eks list-addons --name <cluster-name> --output table

# List available add-ons for this K8s version
aws eks describe-addon-versions \
  --kubernetes-version <k8s-version> \
  --query 'addons[*].addonName' --output table
```

## Step 1: Create core networking add-ons (vpc-cni, coredns, kube-proxy)

### vpc-cni with IRSA

```bash
CLUSTER_NAME=<cluster-name>
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
OIDC_URL=$(aws eks describe-cluster --name $CLUSTER_NAME \
  --query 'cluster.identity.oidc.issuer' --output text | sed 's|https://||')

# Create IAM trust policy for vpc-cni
cat > /tmp/vpc-cni-trust.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_URL}"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "${OIDC_URL}:aud": "sts.amazonaws.com",
        "${OIDC_URL}:sub": "system:serviceaccount:kube-system:aws-node"
      }
    }
  }]
}
EOF

aws iam create-role \
  --role-name AmazonEKSVPCCNIRole \
  --assume-role-policy-document file:///tmp/vpc-cni-trust.json

aws iam attach-role-policy \
  --role-name AmazonEKSVPCCNIRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

# Create the vpc-cni add-on
aws eks create-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name vpc-cni \
  --addon-version v1.18.1-eksbuild.3 \
  --service-account-role-arn arn:aws:iam::${ACCOUNT_ID}:role/AmazonEKSVPCCNIRole \
  --configuration-values '{"env":{"ENABLE_PREFIX_DELEGATION":"true"}}' \
  --resolve-conflicts OVERWRITE
```

### coredns

```bash
aws eks create-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name coredns \
  --addon-version v1.11.1-eksbuild.4 \
  --resolve-conflicts OVERWRITE
```

### kube-proxy

```bash
aws eks create-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name kube-proxy \
  --addon-version v1.30.0-eksbuild.3 \
  --resolve-conflicts OVERWRITE
```

## Step 2: Create the EBS CSI driver add-on with IRSA

```bash
# Create IAM trust policy for EBS CSI
cat > /tmp/ebs-csi-trust.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_URL}"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "${OIDC_URL}:aud": "sts.amazonaws.com",
        "${OIDC_URL}:sub": "system:serviceaccount:kube-system:ebs-csi-controller-sa"
      }
    }
  }]
}
EOF

aws iam create-role \
  --role-name AmazonEBSCSIDriverRole \
  --assume-role-policy-document file:///tmp/ebs-csi-trust.json

# Create a custom policy (or use the managed policy if available)
cat > /tmp/ebs-csi-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["ec2:CreateSnapshot","ec2:AttachVolume","ec2:DetachVolume","ec2:ModifyVolume","ec2:DescribeAvailabilityZones","ec2:DescribeInstances","ec2:DescribeSnapshots","ec2:DescribeTags","ec2:DescribeVolumes","ec2:DescribeVolumesModifications"], "Resource": "*"},
    {"Effect": "Allow", "Action": ["ec2:CreateTags"], "Resource": ["arn:aws:ec2:*:*:volume/*","arn:aws:ec2:*:*:snapshot/*"]},
    {"Effect": "Allow", "Action": ["ec2:DeleteTags"], "Resource": ["arn:aws:ec2:*:*:volume/*","arn:aws:ec2:*:*:snapshot/*"]},
    {"Effect": "Allow", "Action": ["ec2:CreateVolume","ec2:DeleteVolume"], "Resource": "*"},
    {"Effect": "Allow", "Action": ["ec2:DeleteSnapshot"], "Resource": "*"},
    {"Effect": "Allow", "Action": ["ec2:CreateTags","ec2:DeleteTags"], "Resource": ["arn:aws:ec2:*:*:volume/*","arn:aws:ec2:*:*:snapshot/*"]}
  ]
}
EOF

aws iam put-role-policy \
  --role-name AmazonEBSCSIDriverRole \
  --policy-name AmazonEBSCSIDriverPolicy \
  --policy-document file:///tmp/ebs-csi-policy.json

# Create the EBS CSI add-on
aws eks create-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name aws-ebs-csi-driver \
  --addon-version v1.26.0-eksbuild.1 \
  --service-account-role-arn arn:aws:iam::${ACCOUNT_ID}:role/AmazonEBSCSIDriverRole \
  --resolve-conflicts OVERWRITE
```

## Step 3: Set up EKS Pod Identity (alternative to IRSA)

```bash
# Install the Pod Identity Agent add-on
aws eks create-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name eks-pod-identity-agent \
  --resolve-conflicts OVERWRITE

# Create a Pod Identity IAM role
cat > /tmp/pod-identity-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "pods.eks.amazonaws.com"},
    "Action": ["sts:AssumeRole", "sts:TagSession"]
  }]
}
EOF

aws iam create-role \
  --role-name MyPodIdentityRole \
  --assume-role-policy-document file:///tmp/pod-identity-trust.json

# Attach the CNI policy (or any policy the add-on needs)
aws iam attach-role-policy \
  --role-name MyPodIdentityRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

# Create the Pod Identity association
aws eks create-pod-identity-association \
  --cluster-name $CLUSTER_NAME \
  --namespace kube-system \
  --service-account aws-node \
  --role-arn arn:aws:iam::${ACCOUNT_ID}:role/MyPodIdentityRole
```

## Step 4: Create observability add-ons

### metrics-server

```bash
aws eks create-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name metrics-server \
  --addon-version v0.7.0-eksbuild.2 \
  --resolve-conflicts OVERWRITE
```

### ADOT (AWS Distro for OpenTelemetry)

```bash
aws eks create-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name adot \
  --addon-version v0.92.1-eksbuild.1 \
  --resolve-conflicts OVERWRITE
```

### GuardDuty Agent

```bash
aws eks create-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name guardduty-agent \
  --resolve-conflicts OVERWRITE
```

## Step 5: Update an existing add-on

```bash
# Get the current configuration values
CURRENT_CONFIG=$(aws eks describe-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name vpc-cni \
  --query 'addon.configurationValues' --output text)

# Update with new config (merge with existing)
aws eks update-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name vpc-cni \
  --addon-version v1.18.2-eksbuild.1 \
  --configuration-values '{"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"2"}}' \
  --resolve-conflicts PRESERVE
```

## Verification

```bash
# List all add-ons
aws eks list-addons --name $CLUSTER_NAME --output table

# Describe a specific add-on
aws eks describe-addon \
  --cluster-name $CLUSTER_NAME \
  --addon-name vpc-cni \
  --query 'addon.{Name:addonName,Version:addonVersion,Status:status,Health:healthIssues,Config:configurationValues}'

# Verify add-on pods are running
kubectl get pods -n kube-system -l k8s-app=aws-node
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl get pods -n kube-system -l k8s-app=kube-proxy

# Check DaemonSets (vpc-cni, kube-proxy)
kubectl get ds -n kube-system

# Verify IRSA annotation on service account
kubectl get sa aws-node -n kube-system -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}'

# Verify Pod Identity association
aws eks list-pod-identity-associations --cluster-name $CLUSTER_NAME

# Verify EBS CSI controller pods
kubectl get pods -n kube-system -l app=ebs-csi-controller
```

## Terraform equivalent

```hcl
# Data source for cluster
data "aws_eks_cluster" "this" {
  name = "my-cluster"
}

# IAM role for vpc-cni (IRSA)
data "aws_iam_policy_document" "vpc_cni_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::123456789012:oidc-provider/${replace(data.aws_eks_cluster.this.identity[0].oidc[0].issuer, "https://", "")}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(data.aws_eks_cluster.this.identity[0].oidc[0].issuer, "https://", "")}:sub"
      values   = ["system:serviceaccount:kube-system:aws-node"]
    }
  }
}

resource "aws_iam_role" "vpc_cni" {
  name               = "AmazonEKSVPCCNIRole"
  assume_role_policy = data.aws_iam_policy_document.vpc_cni_assume_role.json
}

resource "aws_iam_role_policy_attachment" "vpc_cni" {
  role       = aws_iam_role.vpc_cni.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

# vpc-cni add-on
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = "my-cluster"
  addon_name                  = "vpc-cni"
  addon_version               = "v1.18.1-eksbuild.3"
  service_account_role_arn    = aws_iam_role.vpc_cni.arn
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"
  configuration_values = jsonencode({
    env = { ENABLE_PREFIX_DELEGATION = "true" }
  })
}

# Pod Identity Agent add-on
resource "aws_eks_addon" "pod_identity_agent" {
  cluster_name                = "my-cluster"
  addon_name                  = "eks-pod-identity-agent"
  resolve_conflicts_on_create = "OVERWRITE"
}

# Pod Identity association
resource "aws_eks_pod_identity_association" "vpc_cni" {
  cluster_name     = "my-cluster"
  namespace        = "kube-system"
  service_account  = "aws-node"
  role_arn         = aws_iam_role.vpc_cni.arn
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| List add-ons | `aws eks list-addons` |
| Describe add-on | `aws eks describe-addon` |
| Create add-on | `aws eks create-addon` |
| Update add-on | `aws eks update-addon` |
| Delete add-on | `aws eks delete-addon` |
| List addon versions | `aws eks describe-addon-versions` |
| List Pod Identity associations | `aws eks list-pod-identity-associations` |
| Create Pod Identity association | `aws eks create-pod-identity-association` |
| Delete Pod Identity association | `aws eks delete-pod-identity-association` |

## Configuration values create/update CLI (Step 3) (moved from SKILL.md)

**Set configuration values on creation:**

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.18.1-eksbuild.3 \
  --configuration-values '{"env":{"AWS_VPC_K8S_CNI_LOGLEVEL":"DEBUG","ENABLE_PREFIX_DELEGATION":"true"}}' \
  --resolve-conflicts OVERWRITE
```

**Update configuration values:**

```bash
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --configuration-values '{"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"1"}}' \
  --resolve-conflicts PRESERVE
```


## vpc-cni IRSA role creation CLI (Step 4) (moved from SKILL.md)

**Create an IAM role for vpc-cni (IRSA):**

```bash
CLUSTER_NAME=my-cluster
ACCOUNT_ID=123456789012
OIDC_URL=$(aws eks describe-cluster --name $CLUSTER_NAME \
  --query 'cluster.identity.oidc.issuer' --output text | sed 's|https://||')

# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_URL}"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "${OIDC_URL}:aud": "sts.amazonaws.com",
        "${OIDC_URL}:sub": "system:serviceaccount:kube-system:aws-node"
      }
    }
  }]
}
EOF

aws iam create-role \
  --role-name AmazonEKSVPCCNIRole \
  --assume-role-policy-document file://trust-policy.json

# Attach the managed policy
aws iam attach-role-policy \
  --role-name AmazonEKSVPCCNIRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
```

**Create add-on with IRSA role:**

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --service-account-role-arn arn:aws:iam::${ACCOUNT_ID}:role/AmazonEKSVPCCNIRole \
  --resolve-conflicts OVERWRITE
```


## Pod Identity Agent install CLI (Step 5) (moved from SKILL.md)

**Install the Pod Identity Agent:**

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name eks-pod-identity-agent \
  --resolve-conflicts OVERWRITE
```


## Pod Identity role and association CLI (Step 5) (moved from SKILL.md)

**Create a Pod Identity IAM role:**

```bash
cat > pod-identity-trust.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "pods.eks.amazonaws.com" },
    "Action": ["sts:AssumeRole", "sts:TagSession"]
  }]
}
EOF

aws iam create-role \
  --role-name MyAddonRole \
  --assume-role-policy-document file://pod-identity-trust.json
```

**Create a Pod Identity association:**

```bash
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace kube-system \
  --service-account aws-node \
  --role-arn arn:aws:iam::123456789012:role/MyAddonRole
```


## Hybrid Nodes vpc-cni configuration CLI (Step 7) (moved from SKILL.md)

```bash
# vpc-cni with custom networking for hybrid nodes
aws eks update-addon \
  --cluster-name my-hybrid-cluster \
  --addon-name vpc-cni \
  --configuration-values '{"env":{"AWS_VPC_K8S_CNI_EXTERNALSNAT":"true","CUSTOM_NETWORK_CFG":"true"}}' \
  --resolve-conflicts PRESERVE
```
