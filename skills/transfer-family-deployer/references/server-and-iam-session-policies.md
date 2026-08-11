# Transfer Family Server, IAM Roles, and Session Policies Reference

Load this reference when planning or executing any AWS Transfer Family
server deployment. The procedures below are the canonical server
configurations, IAM execution role setup, and per-user session policy
patterns for each Transfer Family archetype.

## Decision tree — which server archetype

| Scenario | Use | Why |
|---|---|---|
| Consumer / one-off partner SFTP | **Service Managed SFTP, PUBLIC** | SSH keys per user, no IdP infrastructure |
| Regulated partner B2B | **SFTP/FTPS, VPC_ENDPOINT** | Private connectivity, your SGs, your Route 53 |
| Workforce AD auth | **Directory Service SFTP, VPC_ENDPOINT** | DOMAIN\user + AD password, no SSH keys |
| External IdP (Okta, Auth0) | **API Gateway Lambda custom IdP** | Centralized mapping, MFA, audit |
| AS2 B2B app-level | **AS2, VPC_ENDPOINT** | Mutual cert auth, MDN acks |
| Inbound file processing | **Service Managed SFTP + managed workflow** | OnUpload triggers COPY/TAG/CUSTOM steps |

## Service Managed SFTP procedure

**When to use:** small user count, SSH key distribution is feasible.

**Pre-checks:**
1. S3 backend bucket exists in same region.
2. IAM execution role trusts `transfer.amazonaws.com` (ideally with
   `aws:SourceAccount` or `aws:SourceArn` condition).
3. IAM role has S3 permissions on the bucket prefix.
4. Logging role has CloudWatch Logs permissions.
5. Operator holds `transfer:CreateServer` + `iam:PassRole`.

**IAM trust policy (locked to account):**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "transfer.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {"StringEquals": {"aws:SourceAccount": "111111111111"}}
  }]
}
```

**IAM identity policy (max scope — session policy narrows per user):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": "arn:aws:s3:::prod-sftp-inbox"},
    {"Effect": "Allow", "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject"], "Resource": "arn:aws:s3:::prod-sftp-inbox/*"}
  ]
}
```

**Server CLI:**
```bash
aws transfer create-server \
  --description prod-sftp-inbox \
  --protocols SFTP \
  --endpoint-type PUBLIC \
  --identity-provider-type SERVICE_MANAGED \
  --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole \
  --tags Key=Environment,Value=prod
```

## Session policy procedure (per-user scope)

**When to use:** every Service Managed or custom-IdP-mapped user. The
session policy is the effective security boundary — without it the
user inherits the full IAM role scope.

**Session policy JSON (passed via `--policy` on `create-user`):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::prod-sftp-inbox",
      "Condition": {"StringLike": {"s3:prefix": ["alice/*","alice"]}}
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject"],
      "Resource": "arn:aws:s3:::prod-sftp-inbox/alice/*"
    }
  ]
}
```

**create-user CLI:**
```bash
aws transfer create-user \
  --server-id s-abc123def456 \
  --user-name alice \
  --role arn:aws:iam::111111111111:role/TransferUserS3Role \
  --home-directory /prod-sftp-inbox/alice \
  --home-directory-type PATH \
  --ssh-public-key-body "ssh-rsa AAAAB3...alice@laptop" \
  --policy '<session policy JSON above>'
```

**HomeDirectoryType: PATH vs LOGICAL:**

| Type | Behavior | When to use |
|---|---|---|
| `PATH` (default) | Single S3 prefix as home | Simple per-user home dirs |
| `LOGICAL` | Map virtual dirs to different S3 prefixes via `HomeDirectoryMappings` | Chroot-like isolation, multi-folder views |

## Logging role

```bash
aws iam create-role --role-name TransferLoggingRole \
  --assume-role-policy-document file://transfer-trust.json
aws iam attach-role-policy --role-name TransferLoggingRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSTransferLoggingAccess
```

Without a logging role, every user-level operation (upload, download,
list, mkdir) goes unrecorded — no audit trail of who uploaded what.

## Endpoint type comparison

| Type | Networking | When acceptable |
|---|---|---|
| `PUBLIC` | Internet-facing, AWS-managed | SFTP only — acceptable for pilots; FTPS exposes TLS metadata; FTP blocked |
| `VPC` | ENI per subnet in your VPC | Multi-AZ via multiple subnets; you control SGs and DNS |
| `VPC_ENDPOINT` (preferred) | Single VPC endpoint serving all AZs | Production; no per-subnet ENI; preferred for multi-AZ |

## FTPS ACM cert requirements

- ACM cert ARN in the SAME region as the server.
- Status `ISSUED` (not PENDING_VALIDATION, not REJECTED).
- Cert subject or SAN matches the FTPS hostname clients connect to.
- Wildcard certs work for subdomains.
- Import of self-signed certs supported but rejected by most client
  SFTP libraries.

## Pre-flight verification commands

```bash
# S3 bucket exists in same region?
aws s3api head-bucket --bucket prod-sftp-inbox --expected-bucket-owner 111111111111

# IAM execution role trusts transfer.amazonaws.com?
aws iam get-role --role-name TransferUserS3Role \
  --query 'Role.AssumeRolePolicyDocument.Statement[?Principal.Service==`transfer.amazonaws.com`]'

# ACM cert ISSUED and in-region?
aws acm describe-certificate --certificate-arn <arn> --region us-east-1 \
  --query 'Certificate.[Status,SubjectAlternatives]'

# Logging role attached to logging managed policy?
aws iam list-attached-role-policies --role-name TransferLoggingRole \
  --query 'AttachedPolicies[?PolicyArn==`arn:aws:iam::aws:policy/service-role/AWSTransferLoggingAccess`]'

# Server exists?
aws transfer list-servers --query 'Servers[?Description==`prod-sftp-inbox`]'
```

## Token validity and key rotation

- SSH public keys per user (Service Managed). Rotate on departure or
  compromise via `delete-ssh-public-key` + `create-ssh-public-key`.
- For custom IdP: the Lambda returns `PublicKeys` array — keys can be
  rotated without re-deploying the server.
- For Directory Service: AD password rotation is governed by your AD
  password policy — out of Transfer Family scope.
