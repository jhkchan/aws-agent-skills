# File Share and SMB Configuration — Storage Gateway Deployer

Deep reference on NFS/SMB file share configuration (S3 bucket mapping,
default storage class, client lists, object ACLs), SMB Active Directory
integration (domain join, authenticated access, audit logging), guest
access SMB, and file share refresh. Loaded on demand by the skill —
kept out of the main SKILL.md body so the provisioning procedure stays
scannable.

## NFS file share configuration

### Create an NFS file share

```bash
aws storagegateway create-nfs-file-share \
  --client-token unique-token-12345 \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --role arn:aws:iam::123456789012:role/StorageGatewayS3Role \
  --location-arn arn:aws:s3:::my-data-bucket \
  --default-storage-class S3_STANDARD \
  --client-list 10.0.0.0/16 10.1.0.0/16 \
  --squash NoRootSquash \
  --guess-mime-type-enabled \
  --object-acl private \
  --region us-east-1
```

### Key parameters

| Parameter | Options | Default | Notes |
|---|---|---|---|
| `--default-storage-class` | S3_STANDARD, S3_STANDARD_IA, S3_INTELLIGENT_TIERING, S3_GLACIER_IR | S3_STANDARD | Choose based on access patterns |
| `--client-list` | CIDR blocks | (required) | Restrict to known networks |
| `--squash` | NoRootSquash, RootSquash, AllSquash | RootSquash | NoRootSquash allows root access |
| `--object-acl` | private, public-read, public-read-write | private | Use private unless explicitly needed |
| `--guess-mime-type-enabled` | true/false | true | Auto-detect MIME types from extensions |

### Mount the NFS share from a client

```bash
# Install NFS client (if needed)
sudo apt install -y nfs-common  # Debian/Ubuntu
sudo yum install -y nfs-utils   # RHEL/CentOS

# Create mount point
sudo mkdir -p /mnt/gateway

# Mount the NFS share
sudo mount -t nfs -o nolock,hard <gateway-ip>:/<share-name> /mnt/gateway

# Verify
ls /mnt/gateway
```

## SMB file share configuration

### Guest access SMB (no AD)

```bash
aws storagegateway create-smb-file-share \
  --client-token unique-token-guest-12345 \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --role arn:aws:iam::123456789012:role/StorageGatewayS3Role \
  --location-arn arn:aws:s3:::smb-share-bucket \
  --authentication GuestAccess \
  --guest-password "GuestPass123!" \
  --region us-east-1
```

### Active Directory authenticated SMB

```bash
# Step 1: Join the gateway to Active Directory
aws storagegateway join-domain \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --domain-name corp.example.com \
  --organizational-unit "OU=Servers,DC=corp,DC=example,DC=com" \
  --domain-username sgw-service \
  --domain-password "DomainPass123!" \
  --region us-east-1

# Step 2: Create an authenticated SMB file share
aws storagegateway create-smb-file-share \
  --client-token unique-token-ad-12345 \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --role arn:aws:iam::123456789012:role/StorageGatewayS3Role \
  --location-arn arn:aws:s3:::smb-share-bucket \
  --authentication ActiveDirectory \
  --admin-user-list "corp\\sgw-admins" \
  --valid-user-list "corp\\finance-users" \
  --invalid-user-list "corp\\terminated-users" \
  --region us-east-1
```

### AD join prerequisites

| Requirement | Detail |
|---|---|
| DNS resolution | Gateway must resolve the domain controller FQDN |
| Network ports | 53 (DNS), 88 (Kerberos), 389 (LDAP), 445 (SMB), 464 (Kerberos password), 3268 (LDAP GC) |
| Service account | AD account with permission to join computers to the domain |
| OU path | Optional OU for the gateway computer object |

### Verify AD join status

```bash
aws storagegateway describe-smb-settings \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --region us-east-1
# Expected: ActiveDirectoryStatus: "ACCESS_DENIED" or "JOINED"
```

## SMB audit logging

### Enable audit logging

```bash
# Create CloudWatch Logs log group
aws logs create-log-group \
  --log-group-name /aws/storagegateway/sgw-XXXXX-audit \
  --region us-east-1

# Enable audit logging on the gateway
aws storagegateway update-smb-security-strategy \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --smb-security-strategy MandatoryEncryption \
  --region us-east-1
```

### Audit log contents

Each SMB access generates a log entry with:
- User identity (from AD authentication).
- File path accessed.
- Operation type (read, write, delete).
- Timestamp.
- Client IP address.

## File share refresh

### Automatic refresh

File shares can detect objects added directly to S3 (outside the
gateway) via automatic refresh. This is important when other
applications write to the same S3 bucket.

```bash
# Configure automatic refresh
aws storagegateway update-nfs-file-share \
  --file-share-arn arn:aws:storagegateway:us-east-1:123456789012:share/share-XXXXX \
  --file-share-refresh-interval 60 \
  --region us-east-1
```

### On-demand refresh

```bash
# Trigger an immediate refresh
aws storagegateway refresh-cache \
  --file-share-arn arn:aws:storagegateway:us-east-1:123456789012:share/share-XXXXX \
  --region us-east-1
```

## IAM role for file shares

The IAM role used by file shares must have permissions to read/write
the S3 bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:GetBucketVersioning",
        "s3:ListBucketVersions"
      ],
      "Resource": [
        "arn:aws:s3:::my-data-bucket",
        "arn:aws:s3:::my-data-bucket/*"
      ]
    }
  ]
}
```

The role's trust policy must allow Storage Gateway to assume it:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "storagegateway.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## Terraform examples

```hcl
# NFS file share
resource "aws_storagegateway_nfs_file_share" "nfs" {
  gateway_arn            = aws_storagegateway_gateway.main.gateway_arn
  location_arn           = "arn:aws:s3:::my-data-bucket"
  role_arn               = aws_iam_role.gateway_role.arn
  default_storage_class  = "S3_STANDARD"
  client_list            = ["10.0.0.0/16"]
  squash                 = "NoRootSquash"
  guess_mime_type_enabled = true
  object_acl             = "private"

  tags = {
    Environment = "production"
  }
}

# SMB file share with Active Directory
resource "aws_storagegateway_smb_file_share" "smb" {
  gateway_arn       = aws_storagegateway_gateway.main.gateway_arn
  location_arn      = "arn:aws:s3:::smb-share-bucket"
  role_arn          = aws_iam_role.gateway_role.arn
  authentication    = "ActiveDirectory"
  admin_user_list   = ["corp\\sgw-admins"]
  default_storage_class = "S3_STANDARD"

  tags = {
    Environment = "production"
  }
}

# AD domain join
resource "aws_storagegateway_gateway" "main" {
  gateway_name     = "prod-smb-gateway"
  gateway_type     = "FILE_S3"
  gateway_timezone = "GMT-5:00"
  smb_domain_name  = "corp.example.com"
  smb_domain_username = "sgw-service"
  smb_domain_password = "DomainPass123!"
  active_directory_status = "JOINED"
}
```
