# VPC Endpoint Types Reference

Supplementary reference for the VPC Network Deployer skill. Use when
deciding between Gateway and Interface endpoints, estimating costs, and
planning private connectivity for AWS services.

## Gateway vs Interface endpoints

| Dimension | Gateway Endpoint | Interface Endpoint |
|---|---|---|
| Supported services | S3, DynamoDB only | 50+ AWS services (Secrets Manager, SSM, KMS, etc.) |
| Routing mechanism | Route table entry (prefix list) | ENI with private IP in subnet |
| Cost | **FREE** — no per-hour, no per-GB | ~$7.05/month per AZ per endpoint + $0.01/GB |
| DNS behavior | Prefix list in route table overrides S3/DDB public DNS | Private DNS rewrites service hostname to private IP |
| High availability | Inherently HA (AWS backbone) | Requires endpoint per AZ for HA |
| Security group | N/A (route-table-based) | Required (controls which traffic can reach the endpoint ENI) |
| Max per VPC | 20 (soft limit, adjustable) | 50 (soft limit, adjustable) |
| IPv6 support | Yes | Yes |

## When to use Gateway endpoints

**Always.** For S3 and DynamoDB, Gateway Endpoints are free and route
through the AWS backbone instead of the internet. There is no scenario
where a Gateway Endpoint is worse than routing through NAT.

**Cost-savings example:** A workload pulling 1 TB/month from S3 through a
NAT Gateway costs $45.90/month in NAT data processing. With a Gateway
Endpoint, this drops to $0. The Gateway Endpoint pays for itself on day
one.

**Deployment:**
```
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --vpc-endpoint-type Gateway \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids rtb-public rtb-private-a rtb-private-b rtb-private-c
```

**Critical:** Add the Gateway Endpoint to EVERY route table that needs
S3/DynamoDB access from private subnets. New route tables created later
do NOT inherit the endpoint — add them explicitly.

## When to use Interface endpoints

Use Interface Endpoints for AWS services accessed from private subnets
when:
1. The service is NOT S3 or DynamoDB (no Gateway option).
2. You need the API call to stay on the AWS backbone (no NAT egress).
3. Compliance requires no internet egress for the API.

**Common Interface Endpoints for a production VPC:**

| Service | Endpoint name | Why |
|---|---|---|
| Secrets Manager | `com.amazonaws.<region>.secretsmanager` | Secret retrieval without NAT |
| SSM | `com.amazonaws.<region>.ssm` | Session Manager, Parameter Store |
| SSM Messages | `com.amazonaws.<region>.ssmmessages` | Session Manager data channel |
| KMS | `com.amazonaws.<region>.kms` | KMS API for decrypt |
| CloudWatch Logs | `com.amazonaws.<region>.logs` | Log delivery |
| STS | `com.amazonaws.<region>.sts` | AssumeRole for cross-account |
| ECR API | `com.amazonaws.<region>.ecr.api` | ECR API calls |
| ECR Docker | `com.amazonaws.<region>.ecr.dkr` | Docker image pulls |
| CloudFormation | `com.amazonaws.<region>.cloudformation` | Stack operations |

**Cost calculation (3-AZ VPC):**
- 9 endpoints × 3 AZs × $7.05/month = ~$190/month
- Plus $0.01/GB data processed (usually minimal for API calls)

**Cost-optimization:** Only deploy Interface Endpoints for services you
actually use from private subnets. A common mistake is deploying every
possible endpoint "just in case" — the per-AZ cost adds up quickly.

## Interface Endpoint deployment

```
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.secretsmanager \
  --subnet-ids subnet-private-a subnet-private-b subnet-private-c \
  --security-group-ids sg-endpoint-xxx \
  --private-dns-enabled
```

**private-dns-enabled:** Rewrites `secretsmanager.us-east-1.amazonaws.com`
to the endpoint's private IP within the VPC. Without this, SDKs that
construct URLs from the public DNS name route traffic through the NAT
Gateway — defeating the endpoint's purpose.

**Security group for Interface Endpoints:** Allow inbound 443/tcp from
the consuming security group (e.g., `sg-app`). The endpoint ENI inherits
this SG.

## Private DNS considerations

`--private-dns-enabled` has a constraint: only ONE Interface Endpoint per
service per VPC can have private DNS enabled. If you deploy a second
endpoint for the same service (e.g., for a different network segment),
private DNS must be disabled on the duplicate.

**Multi-VPC with AWS PrivateLink consumer:** When consuming a
PrivateLink service from another account, the Interface Endpoint does
NOT support private DNS by default. Applications must use the
endpoint-specific DNS name (`vpce-xxx.yyy.zzz.vpce.amazonaws.com`).

## Endpoint policies

Both Gateway and Interface endpoints support **endpoint policies** — a
resource-based policy that controls which API calls are allowed through
the endpoint.

**S3 Gateway Endpoint policy (restrict to specific buckets):**
```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": [
        "arn:aws:s3:::prod-app-assets/*",
        "arn:aws:s3:::prod-app-artifacts/*"
      ]
    },
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "NotResource": [
        "arn:aws:s3:::prod-app-assets/*",
        "arn:aws:s3:::prod-app-artifacts/*"
      ]
    }
  ]
}
```

This prevents the endpoint from being used to exfiltrate data to other
S3 buckets. Without this policy, any S3 API call (including `s3:PutObject`
to an attacker's bucket) routes through the endpoint.
