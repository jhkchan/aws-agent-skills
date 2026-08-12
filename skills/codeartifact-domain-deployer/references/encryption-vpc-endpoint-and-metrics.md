# Encryption, VPC Endpoint, and Metrics — CodeArtifact Domain Deployer

Deep reference on KMS encryption (AWS-managed vs CMK, immutability,
key policy requirements), VPC interface endpoints (dual-endpoint
requirement, private DNS, security groups), lifecycle policies
(retention rules, package version cleanup), and CloudWatch metrics
for monitoring. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## KMS encryption

### AWS-managed key (default)

By default, CodeArtifact uses an AWS-managed KMS key. This key is
created and managed by AWS — you do not see it in your account, and
you cannot control its rotation policy.

```bash
# Create domain with default AWS-managed key (omit --encryption-key)
aws codeartifact create-domain \
  --domain my-domain \
  --region us-east-1
```

### Customer-managed key (CMK)

For enterprise compliance, use a CMK. You control the key policy,
rotation, and cross-account access.

```bash
# Create a CMK
KMS_KEY_ID=$(aws kms create-key \
  --description "CodeArtifact domain encryption key" \
  --policy file://kms-key-policy.json \
  --query 'KeyMetadata.KeyId' --output text \
  --region us-east-1)

# Create domain with CMK (IMMUTABLE — cannot change later)
aws codeartifact create-domain \
  --domain my-domain \
  --encryption-key arn:aws:kms:us-east-1:123456789012:key/$KMS_KEY_ID \
  --region us-east-1
```

### CMK key policy

The CMK key policy MUST allow CodeArtifact to use the key. Without
this, the domain creation will succeed but repository operations will
fail.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCodeArtifactService",
      "Effect": "Allow",
      "Principal": {
        "Service": "codeartifact.amazonaws.com"
      },
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowDomainOwner",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:root"
      },
      "Action": "kms:*",
      "Resource": "*"
    }
  ]
}
```

### Encryption immutability

**The encryption key is set at domain creation and CANNOT be changed.**

```text
Domain created with AWS-managed key
  → Cannot switch to CMK later (must recreate domain + repos)

Domain created with CMK
  → Cannot switch to AWS-managed key
  → Cannot switch to a different CMK
  → CAN rotate the CMK (KMS key ID stays the same, backing key changes)
```

**Decision framework:**

| Requirement | Use CMK? |
|---|---|
| Compliance requires customer-controlled keys (HIPAA, PCI, FedRAMP) | Yes |
| Need cross-account key access | Yes |
| Need custom key rotation schedule | Yes |
| Simple internal use, no compliance requirement | No (default is fine) |
| Need to change encryption after domain creation | Impossible — plan ahead |

## VPC interface endpoint

### Why two endpoints are needed

CodeArtifact has two service endpoints: the API endpoint (for
management calls like `create-domain`, `login`, `get-authorization-
token`) and the repositories endpoint (for package download/upload
like `npm install`, `npm publish`). Both need VPC endpoints for
fully private access.

```text
codeartifact.api.<region>.amazonaws.com
  → Management API (login, get-authorization-token, describe-*)

codeartifact.repositories.<region>.amazonaws.com
  → Package data (npm install, pip install, npm publish)

Without BOTH endpoints:
  ├── Missing API endpoint → login/token generation fails
  └── Missing repositories endpoint → package download/upload fails
```

### Creating both endpoints

```bash
# API endpoint
API_VPCE=$(aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.codeartifact.api \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --security-group-ids sg-priv-1 \
  --private-dns-enabled \
  --region us-east-1 \
  --query 'VpcEndpoints[0].VpcEndpointId' --output text)

# Repositories endpoint
REPO_VPCE=$(aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.codeartifact.repositories \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --security-group-ids sg-priv-1 \
  --private-dns-enabled \
  --region us-east-1 \
  --query 'VpcEndpoints[0].VpcEndpointId' --output text)

echo "API endpoint: $API_VPCE"
echo "Repositories endpoint: $REPO_VPCE"
```

### Private DNS requirement

`--private-dns-enabled` is REQUIRED. Without it:

```text
Without private DNS:
  → npm resolves my-domain-xxx.d.codeartifact.us-east-1.amazonaws.com
  → Gets the PUBLIC IP (not the VPC endpoint)
  → Traffic goes over the internet (defeats the purpose)

With private DNS:
  → Route 53 private hosted zone intercepts the CodeArtifact hostname
  → Resolves to the VPC endpoint's private IP
  → Traffic stays within the VPC (private)
```

### VPC endpoint policy

By default, VPC endpoints allow full access. For tighter security,
attach a policy:

```bash
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-aaa111 \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": "*",
        "Action": [
          "codeartifact:GetAuthorizationToken",
          "codeartifact:ReadFromRepository",
          "codeartifact:GetRepositoryEndpoint"
        ],
        "Resource": "*"
      }
    ]
  }' \
  --region us-east-1
```

### Security group requirements

The VPC endpoint's security group must allow inbound HTTPS (443) from
the subnets that will access CodeArtifact:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-priv-1 \
  --ip-permissions "IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges=[{CidrIp=10.0.0.0/16}]" \
  --region us-east-1
```

## Lifecycle policy

### Why lifecycle policies matter

CodeArtifact charges for storage. Without lifecycle policies, old
package versions accumulate indefinitely. Lifecycle policies automate
retention.

### Configuration

```bash
# Retain last N versions per package
aws codeartifact put-lifecycle-configuration \
  --domain my-domain \
  --repository my-team-packages \
  --lifecycle-configuration '{
    "rules": [
      {
        "rulePriority": 1,
        "description": "Keep last 50 versions per package",
        "actions": [
          {
            "type": "retention",
            "maxVersions": 50
          }
        ]
      }
    ]
  }' \
  --region us-east-1

# Delete package versions older than N days
aws codeartifact put-lifecycle-configuration \
  --domain my-domain \
  --repository my-team-packages \
  --lifecycle-configuration '{
    "rules": [
      {
        "rulePriority": 1,
        "description": "Delete versions older than 180 days",
        "actions": [
          {
            "type": "retention",
            "maxAgeDays": 180
          }
        ]
      }
    ]
  }' \
  --region us-east-1
```

### Retroactivity

Lifecycle policies apply to FUTURE evaluations. When the policy is
first applied, it evaluates existing versions and removes those that
match the rules. After that, it runs on new versions as they are
published.

**Warning:** test lifecycle policies in a non-production repository
first. A misconfigured policy can delete package versions that are
still needed. Deleted versions are NOT recoverable (immutability does
not protect against lifecycle-driven deletion).

## CloudWatch metrics

### Available metrics

| Metric | Dimensions | Description |
|---|---|---|
| `PublishPackageVersion` | DomainName, RepositoryName | Count of package versions published |
| `DownloadPackageVersion` | DomainName, RepositoryName | Count of package versions downloaded |
| `AssetSizeBytes` | DomainName, RepositoryName | Storage consumed by package assets |

### Monitoring queries

```bash
# Track publish rate over the last 7 days
aws cloudwatch get-metric-statistics \
  --namespace AWS/CodeArtifact \
  --metric-name PublishPackageVersion \
  --start-time 2026-08-04T00:00:00Z \
  --end-time 2026-08-11T00:00:00Z \
  --period 86400 \
  --statistics Sum \
  --dimensions Name=DomainName,Value=my-domain Name=RepositoryName,Value=my-team-packages \
  --region us-east-1

# Track download rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/CodeArtifact \
  --metric-name DownloadPackageVersion \
  --start-time 2026-08-04T00:00:00Z \
  --end-time 2026-08-11T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --dimensions Name=DomainName,Value=my-domain \
  --region us-east-1
```

### Recommended CloudWatch alarms

```bash
# Alarm: unusual publish spike (possible supply-chain incident)
aws cloudwatch put-metric-alarm \
  --alarm-name codeartifact-publish-spike \
  --namespace AWS/CodeArtifact \
  --metric-name PublishPackageVersion \
  --dimensions Name=DomainName,Value=my-domain \
  --statistic Sum \
  --period 3600 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:codeartifact-alerts \
  --region us-east-1

# Alarm: storage growth (cost monitoring)
aws cloudwatch put-metric-alarm \
  --alarm-name codeartifact-storage-growth \
  --namespace AWS/CodeArtifact \
  --metric-name AssetSizeBytes \
  --dimensions Name=DomainName,Value=my-domain \
  --statistic Average \
  --period 86400 \
  --threshold 10737418240 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:codeartifact-alerts \
  --region us-east-1
```

## Terraform examples

```hcl
# VPC endpoints for CodeArtifact (both required)
resource "aws_vpc_endpoint" "codeartifact_api" {
  vpc_id              = aws_vpc.main.id
  vpc_endpoint_type   = "Interface"
  service_name        = "com.amazonaws.us-east-1.codeartifact.api"
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  security_group_ids  = [aws_security_group.codeartifact.id]
  private_dns_enabled = true
}

resource "aws_vpc_endpoint" "codeartifact_repos" {
  vpc_id              = aws_vpc.main.id
  vpc_endpoint_type   = "Interface"
  service_name        = "com.amazonaws.us-east-1.codeartifact.repositories"
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  security_group_ids  = [aws_security_group.codeartifact.id]
  private_dns_enabled = true
}

# Security group for VPC endpoints
resource "aws_security_group" "codeartifact" {
  name        = "codeartifact-vpce"
  description = "Allow HTTPS from VPC to CodeArtifact endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }
}

# Lifecycle policy
resource "aws_codeartifact_repository" "npm" {
  domain     = aws_codeartifact_domain.main.name
  repository = "my-team-packages"
}

# Note: lifecycle configuration in Terraform uses the
# aws_codeartifact_repository_domain_lifecycle_policy or
# put-lifecycle-configuration via local-exec provisioner
```
