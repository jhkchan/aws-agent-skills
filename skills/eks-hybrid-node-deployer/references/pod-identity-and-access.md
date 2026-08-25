# Pod Identity and Node Access — EKS Hybrid Node Deployer

Deep reference on pod identity for hybrid nodes (no IMDS, no EC2
instance profile, pod identity agent required), SSM Session Manager
for remote access (keyless, audited, replaces SSH bastion), and
CloudWatch agent for health monitoring. Loaded on demand by the skill —
kept out of the main SKILL.md body so the provisioning procedure stays
scannable.

## Pod identity on hybrid nodes

### How pod identity differs from managed node groups

| Feature | Managed Node Group (EC2) | Hybrid Node (on-prem) |
|---|---|---|
| IMDS | Available (EC2 metadata) | NOT available (no EC2) |
| Instance profile | EC2 instance profile | NOT used (on-prem) |
| Pod identity agent | Runs via IMDS | Runs via activation-based auth |
| Credential source | EC2 metadata service | Node IAM role via activation |
| Association API | Same (EKS Pod Identity) | Same (EKS Pod Identity) |

The EKS Pod Identity API is the same for both managed and hybrid nodes.
The difference is HOW the pod identity agent obtains credentials on the
node. On EC2, it uses IMDS. On hybrid nodes, it uses the node's IAM
role (referenced by the activation code) to assume pod-level IAM roles.

### Installing the pod identity agent on hybrid nodes

```bash
# On the on-prem node (via nodeadm):
nodeadm enable-pod-identity \
  --role arn:aws:iam::123456789012:role/EKSHybridNodeRole

# Verify the agent is running
systemctl status amazon-eks-pod-identity-agent
```

The agent intercepts pod requests for AWS credentials and exchanges
the node's IAM role for the pod-level IAM role defined by the pod
identity association.

### Creating a pod identity association

```bash
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace production \
  --service-account my-app-sa \
  --role-arn arn:aws:iam::123456789012:role/MyAppPodRole
```

Pods using `serviceAccountName: my-app-sa` in the `production` namespace
will automatically receive credentials for `MyAppPodRole`.

### Verifying pod identity

```bash
# List all pod identity associations
aws eks list-pod-identity-associations \
  --cluster-name my-cluster \
  --query 'associations[*].{Namespace:namespace,SA:serviceAccount,Role:roleArn}' \
  --output table

# From inside a pod, verify credentials
kubectl exec -it <pod-name> -- env | grep AWS_
# Should show AWS_ROLE_ARN pointing to MyAppPodRole
```

### Common pod identity pitfalls

1. **Agent not running on hybrid node.** The pod identity agent must be
   explicitly enabled via `nodeadm enable-pod-identity`. Without it,
   pods get no AWS credentials.

2. **Wrong service account name.** The pod's `serviceAccountName` must
   exactly match the association's `serviceAccount`. Case-sensitive.

3. **Trust policy misconfigured.** The pod-level IAM role's trust policy
   must allow `pods.eks.amazonaws.com` to assume it:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "pods.eks.amazonaws.com"},
      "Action": ["sts:AssumeRole","sts:TagSession"]
    }
  ]
}
```

4. **Namespace mismatch.** The association is namespace-scoped. A pod
   in `staging` namespace cannot use a `production` namespace association.

## SSM Session Manager for remote access

### Why SSM instead of SSH

| Feature | SSH (bastion) | SSM Session Manager |
|---|---|---|
| Authentication | SSH keys (manage + rotate) | IAM-based (no keys) |
| Firewall | Open port 22 (attack surface) | No inbound ports needed |
| Audit trail | Manual logging | Automatic CloudTrail logging |
| Access control | OS-level users | IAM policies |
| Network path | Requires bastion in VPC | Outbound 443 to SSM endpoints |

SSM Session Manager is the recommended approach for hybrid node access.

### Registering an on-prem node as an SSM managed instance

```bash
# Create a managed-instance activation
ACTIVATION=$(aws ssm create-activation \
  --iam-role EKSHybridSSMRole \
  --registration-limit 10 \
  --tags Key=Cluster,Value=prod-cluster \
  --expiration-date $(date -u -v+30d +"%Y-%m-%dT%H:%M:%SZ"))

ACTIVATION_ID=$(echo "$ACTIVATION" | jq -r '.ActivationId')
ACTIVATION_CODE=$(echo "$ACTIVATION" | jq -r '.ActivationCode')

echo "Activation ID: $ACTIVATION_ID"
echo "Activation Code: $ACTIVATION_CODE"

# On the on-prem node:
# sudo amazon-ssm-agent -register \
#   -code "$ACTIVATION_CODE" \
#   -id "$ACTIVATION_ID" \
#   -region us-east-1

# Then start the SSM agent:
# sudo systemctl start amazon-ssm-agent
# sudo systemctl enable amazon-ssm-agent
```

### Starting a session

```bash
# List managed instances
aws ssm describe-instance-information \
  --query 'InstanceInformationList[*].{ID:InstanceId,Name:Name,Ping:PingStatus,IP:IPAddress}' \
  --output table

# Start an interactive shell session
aws ssm start-session --target mi-xxxxxxxxxxxxxxxxx

# Run a single command (non-interactive)
aws ssm send-command \
  --instance-ids mi-xxxxxxxxxxxxxxxxx \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["kubectl get nodes","systemctl status kubelet"]' \
  --query 'Command.CommandId' --output text

# Get command output
aws ssm get-command-invocation \
  --command-id <command-id> \
  --instance-id mi-xxxxxxxxxxxxxxxxx \
  --query 'StandardOutputContent' --output text
```

### SSM IAM role for hybrid nodes

The SSM role needs `AmazonSSMManagedInstanceCore` plus any additional
permissions for Session Manager logging:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ssmmessages:CreateControlChannel","ssmmessages:CreateDataChannel","ssmmessages:OpenControlChannel","ssmmessages:OpenDataChannel"],
      "Resource": "*"
    }
  ]
}
```

## CloudWatch agent for health monitoring

### Why CloudWatch is NOT automatic on hybrid nodes

Managed node groups (EC2) get CloudWatch metrics automatically via the
EC2 integration. Hybrid nodes are NOT EC2 instances — they do not appear
in EC2 metrics. The CloudWatch agent must be manually installed and
configured on each on-prem node.

### Installation

```bash
# On the on-prem node (Amazon Linux):
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -U amazon-cloudwatch-agent.rpm

# Ubuntu:
# wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
# sudo dpkg -i amazon-cloudwatch-agent.deb
```

### Configuration

Create a JSON config at
`/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`:

```json
{
  "agent": {"metrics_collection_interval": 60},
  "metrics": {
    "metrics_collected": {
      "cpu": {"measurement": ["cpu_usage_idle","cpu_usage_iowait","cpu_usage_user"], "metrics_collection_interval": 60},
      "mem": {"measurement": ["mem_used_percent","mem_available"], "metrics_collection_interval": 60},
      "disk": {"measurement": ["used_percent","inodes_free"], "resources": ["/","/var/lib/containerd"], "metrics_collection_interval": 60},
      "net": {"measurement": ["bytes_sent","bytes_recv"], "metrics_collection_interval": 60}
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {"file_path": "/var/log/kubelet.log", "log_group_name": "/eks/hybrid/kubelet", "log_stream_name": "{hostname}"},
          {"file_path": "/var/log/containerd/containerd.log", "log_group_name": "/eks/hybrid/containerd", "log_stream_name": "{hostname}"},
          {"file_path": "/var/log/messages", "log_group_name": "/eks/hybrid/system", "log_stream_name": "{hostname}"}
        ]
      }
    }
  }
}
```

```bash
sudo systemctl start amazon-cloudwatch-agent
sudo systemctl enable amazon-cloudwatch-agent
```

### Key metrics to monitor

| Metric | Source | Alert threshold |
|---|---|---|
| kubelet running | systemctl | Not running = critical |
| CPU usage | CloudWatch agent | > 85% sustained |
| Memory usage | CloudWatch agent | > 90% |
| Disk usage | CloudWatch agent | > 85% |
| Node Ready status | kubectl/API | NotReady for > 5 min |
| Pod restart count | kubectl/API | > 5 restarts in 10 min |
| Network latency to API | Custom probe | > 100ms sustained |

### CloudWatch alarms

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name eks-hybrid-high-cpu \
  --metric-name cpu_usage_idle \
  --namespace CWAgent \
  --statistic Average \
  --period 300 \
  --threshold 15 \
  --comparison-operator LessThanThreshold \
  --dimensions Name=hostname,Value=on-prem-node-01 \
  --evaluation-periods 2 \
  --alarm-actions <sns-topic-arn>
```

## Terraform example

```hcl
# Hybrid node IAM role
resource "aws_iam_role" "hybrid_node" {
  name = "EKSHybridNodeRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "hybrid_ecr" {
  role       = aws_iam_role.hybrid_node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy_attachment" "hybrid_ssm" {
  role       = aws_iam_role.hybrid_node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "hybrid_cw" {
  role       = aws_iam_role.hybrid_node.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# EKS access entry for hybrid nodes
resource "aws_eks_access_entry" "hybrid" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = aws_iam_role.hybrid_node.arn
  type          = "HYBRID_LINUX"
}

# Pod identity association
resource "aws_eks_pod_identity_association" "app" {
  cluster_name    = aws_eks_cluster.main.name
  namespace       = "production"
  service_account = "my-app-sa"
  role_arn        = aws_iam_role.app_pod.arn
}
```

## Expert heuristic: pod identity on hybrid nodes (moved from SKILL.md)

A baseline model assumes pod identity works the same as managed node
groups. The correct heuristic recognizes the differences.

```text
Managed Node Group (EC2):
  ├── EKS Pod Identity association maps SA → IAM role
  ├── Pod identity agent uses IMDS from EC2
  └── EC2 instance profile provides baseline node permissions

Hybrid Node (on-prem):
  ├── EKS Pod Identity association maps SA → IAM role (SAME API)
  ├── Pod identity agent must run on-prem (NO IMDS available)
  │     └── Agent obtains credentials via activation-based auth
  ├── NO EC2 instance profile (on-prem is not EC2)
  └── Node IAM role is referenced by activation code registration
```

**Key implication:** the pod identity agent must be explicitly installed
and configured on hybrid nodes. The node's IAM role (created in Step 1)
is what the agent uses to obtain credentials.


## Pod identity agent and association CLI (Step 4) (moved from SKILL.md)

**Step 1: Install the pod identity agent on the on-prem node:**

```bash
./nodeadm enable-pod-identity \
  --role arn:aws:iam::123456789012:role/EKSHybridNodeRole
```

**Step 2: Create a pod identity association in the EKS cluster:**

```bash
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace production \
  --service-account my-app-sa \
  --role-arn arn:aws:iam::123456789012:role/MyAppPodRole
```


## SSM Session Manager activation CLI (Step 10) (moved from SKILL.md)

```bash
# Create a managed-instance activation (registers on-prem as SSM managed)
aws ssm create-activation \
  --iam-role EKSHybridSSMRole \
  --registration-limit 10 \
  --expiration-date $(date -u -v+30d +"%Y-%m-%dT%H:%M:%SZ")

# On the on-prem node: register with SSM using returned code+id
# sudo amazon-ssm-agent -register -code <code> -id <id> -region us-east-1

# Start a session
aws ssm start-session --target mi-xxxxxxxxxxxxxxxxx
```
