# STS Migration Patterns Reference

Supplementary reference for the IAM Key Rotation Automator skill. Use
when migrating from permanent IAM access keys to STS temporary
credentials — the permanent fix that eliminates the need for key
rotation entirely.

## Why migrate to STS?

Permanent access keys are a security liability:
- They never expire (until manually rotated or deleted).
- They can be exfiltrated and used from anywhere.
- Rotation is operationally complex (overlap windows, app config
  updates, cross-account sync).

STS temporary credentials solve all three:
- They expire automatically (15min-12hr).
- They are scoped to a specific session and role.
- No rotation needed — the SDK auto-refreshes.

## Migration patterns by workload type

### Pattern 1: EC2 instance → IAM instance role

The simplest and most impactful migration. EC2 instances support IAM
roles natively — no access key needed.

**Before (permanent key on EC2):**

```python
s3 = boto3.client('s3',
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'])
```

**After (instance role):**

```python
# Remove the access key from env vars.
# Attach an IAM instance profile to the EC2 instance.
# The SDK auto-discovers credentials from instance metadata.
s3 = boto3.client('s3')  # No keys needed!
```

**Migration steps:**

```bash
# 1. Create the IAM role with required permissions
aws iam create-role --role-name EC2AppRole \
  --assume-role-policy-document file://ec2-trust-policy.json

# 2. Attach the permissions policy
aws iam put-role-policy --role-name EC2AppRole \
  --policy-name AppS3DynamoDB \
  --policy-document file://app-permissions.json

# 3. Create an instance profile
aws iam create-instance-profile --instance-profile-name EC2AppProfile
aws iam add-role-to-instance-profile \
  --instance-profile-name EC2AppProfile --role-name EC2AppRole

# 4. Attach to the running instance
aws ec2 associate-iam-instance-profile \
  --instance-id i-0abc123def \
  --iam-instance-profile Name=EC2AppProfile

# 5. Remove environment variables from the app config
# 6. Restart the application
# 7. Verify it works without the access key
# 8. Deactivate and delete the IAM user's access key
```

**ec2-trust-policy.json:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

### Pattern 2: ECS/Fargage task → IAM task role

ECS tasks support IAM roles natively. No access key needed.

**Migration steps:**

```bash
# 1. Create the task role
aws iam create-role --role-name ECSTaskRole \
  --assume-role-policy-document file://ecs-trust-policy.json

# 2. Update the task definition
aws ecs register-task-definition \
  --family my-app \
  --task-role-arn arn:aws:iam::111111111111:role/ECSTaskRole \
  --execution-role-arn arn:aws:iam::111111111111:role/ecsTaskExecutionRole \
  --container-definitions file://containers.json

# 3. Deploy the new task definition
# 4. The SDK auto-discovers credentials from the task metadata endpoint
# 5. Remove access key from container environment
# 6. Deactivate and delete the IAM user's access key
```

**ecs-trust-policy.json:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

### Pattern 3: EKS pod → IRSA (IAM Roles for Service Accounts)

EKS pods use IRSA to assume IAM roles via Kubernetes service accounts.

**Migration steps:**

```bash
# 1. Create the IAM role with an OIDC trust policy
aws iam create-role --role-name EKSPodRole \
  --assume-role-policy-document file://irsa-trust-policy.json

# 2. Create a Kubernetes service account annotated with the role ARN
kubectl create serviceaccount app-sa
kubectl annotate serviceaccount app-sa \
  eks.amazonaws.com/role-arn=arn:aws:iam::111111111111:role/EKSPodRole

# 3. Update the pod spec to use the service account
# 4. The SDK auto-discovers credentials from IRSA
# 5. Remove access key from pod environment
# 6. Deactivate and delete the IAM user's access key
```

### Pattern 4: Lambda function → IAM execution role

Lambda functions use IAM execution roles natively. No access key needed.

```bash
# 1. Create the execution role (if not already created)
aws iam create-role --role-name LambdaAppRole \
  --assume-role-policy-document file://lambda-trust-policy.json

# 2. Update the Lambda function's role
aws lambda update-function-configuration \
  --function-name my-app \
  --role arn:aws:iam::111111111111:role/LambdaAppRole

# 3. Remove access key from Lambda environment variables
# 4. The SDK auto-discovers credentials from the execution role
```

### Pattern 5: On-premises application → STS assume-role

For applications running outside AWS, use a minimal IAM user that can
ONLY call `sts:AssumeRole`. The permanent key is scoped to a single
API call — all actual AWS access uses temporary credentials.

**Minimal IAM user policy (scoped to assume-role only):**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "sts:AssumeRole",
    "Resource": "arn:aws:iam::111111111111:role/OnPremAppRole"
  }]
}
```

**Application-side code:**

```python
import boto3

# Minimal key — can ONLY assume the role
sts = boto3.client('sts',
    aws_access_key_id='AKIAMINIMAL',
    aws_secret_access_key='minimal-secret')

# Assume the role with broader permissions
assumed = sts.assume_role(
    RoleArn='arn:aws:iam::111111111111:role/OnPremAppRole',
    RoleSessionName='onprem-app',
    DurationSeconds=3600
)

# All AWS calls use temporary credentials
s3 = boto3.client('s3',
    aws_access_key_id=assumed['Credentials']['AccessKeyId'],
    aws_secret_access_key=assumed['Credentials']['SecretAccessKey'],
    aws_session_token=assumed['Credentials']['SessionToken'])

# Auto-refresh: the SDK handles this if you use a Session
# For longer-running sessions, implement a credential refresh loop
```

### Pattern 6: Third-party SaaS → Web Identity Federation

For third-party SaaS integrations (GitHub Actions, GitLab CI, etc.),
use Web Identity Federation to assume a role without any permanent key.

**GitHub Actions example:**

```yaml
# .github/workflows/deploy.yml
permissions:
  id-token: write  # Required for OIDC

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: arn:aws:iam::111111111111:role/GitHubActionsDeploy
          aws-region: us-east-1
      # No access key needed — OIDC handles authentication
```

## Migration verification checklist

Before deleting the permanent access key:

- [ ] New credential mechanism deployed (instance role / task role / IRSA / STS)
- [ ] Application restarted with new mechanism active
- [ ] Application verified — all AWS API calls succeed with new credentials
- [ ] Access advisor confirms old key NOT used in 72 hours
- [ ] Old key deactivated (not deleted yet)
- [ ] Application re-verified after deactivation
- [ ] 72 hours pass with no issues
- [ ] Old key deleted
- [ ] IAM user cleaned up (if no longer needed)
- [ ] Documentation updated

## Migration metrics

Track migration progress across the fleet:

| Metric | How to measure | Target |
|---|---|---|
| Permanent keys remaining | `iam list-access-keys` per user | 0 (for AWS compute workloads) |
| STS assume-role calls per day | CloudTrail `AssumeRole` event count | Increasing |
| Key rotation incidents per quarter | CloudTrail + ticketing system | Decreasing to 0 |
| Security Hub IAM.6/IAM.7 findings | Security Hub | 0 |

## Common migration failures

| Failure | Cause | Fix |
|---|---|---|
| App cannot find credentials after role attachment | App hardcodes key in config | Remove hardcoded keys; let SDK auto-discover |
| Instance role permissions too narrow | Role policy missing required actions | Use IAM Access Analyzer to identify missing permissions |
| IRSA not working | OIDC provider not configured on EKS cluster | Associate OIDC provider with the cluster |
| STS assume-role fails from on-prem | Trust policy does not include the IAM user | Add the user ARN to the role's trust policy |
| Credential refresh gap in long-running process | STS credentials expire mid-process | Implement credential refresh loop or use Session with auto-refresh |

## Step 11 — STS temporary credentials migration (from SKILL.md § Step 11)

```python
# Before: static key
s3 = boto3.client('s3', aws_access_key_id='AKIAOLD', aws_secret_access_key='old')

# After: STS assume role (auto-refreshing)
sts = boto3.client('sts')
assumed = sts.assume_role(RoleArn='arn:aws:iam::111111111111:role/AppS3Access',
                          RoleSessionName='app-session')
s3 = boto3.client('s3',
    aws_access_key_id=assumed['Credentials']['AccessKeyId'],
    aws_secret_access_key=assumed['Credentials']['SecretAccessKey'],
    aws_session_token=assumed['Credentials']['SessionToken'])
```

For EC2/ECS/EKS: use instance/task/pod roles directly — the SDK
auto-discovers credentials. No code change needed beyond removing the
static keys.
