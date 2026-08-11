# Identity Providers and Endpoints — Transfer Family Deployer

Deep reference on Transfer Family identity providers (service-managed,
AWS Directory Service, custom Lambda) and endpoint types (PUBLIC, VPC,
VPC_ENDPOINT). Includes authentication flows, Lambda response format,
VPC endpoint networking, and security group configuration. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Identity provider comparison

| Provider | Protocols | Auth method | User management | Best for |
|---|---|---|---|---|
| Service-managed | SFTP | SSH public key | `create-user` per user | Simple SFTP, known users |
| AWS Directory Service | SFTP, FTPS, FTP | AD password | Via AD users/groups | Enterprise AD integration |
| Custom (Lambda) | SFTP, FTPS, FTP | Password or SSH key | Dynamic (Lambda decides) | External IdP, MFA, custom logic |

## Service-managed identity provider

Each user is created via `create-user` with an SSH public key stored
in Transfer Family. The user authenticates by presenting the
corresponding private key during the SSH handshake.

```bash
# Create user with SSH key
aws transfer create-user \
  --server-id s-xxx \
  --user-name partner-a \
  --role arn:aws:iam::123456789012:role/TransferFamilyS3 \
  --home-directory-type LOGICAL \
  --home-directory-mappings Entry=/,Target=/partner-exchange/home/partner-a \
  --ssh-public-key-body "ssh-rsa AAAAB3NzaC1yc2E..."

# Upload additional SSH key (up to 5 per user)
aws transfer import-ssh-public-key \
  --server-id s-xxx \
  --ssh-public-key-body "ssh-rsa AAAAB3NzaC1yc2E..." \
  --user-name partner-a
```

## AWS Directory Service identity provider

Integrates with AWS Managed Microsoft AD. Users authenticate with
their AD credentials (password). No per-user creation needed — AD
users are recognized automatically.

```bash
aws transfer create-server \
  --protocols SFTP \
  --identity-provider-type DIRECTORY_SERVICE \
  --directory-id d-xxx
```

Group-based home directory mapping is supported via AD group membership.

## Custom Lambda identity provider

A Lambda function receives the username and credential (password or
SSH key) and returns the user's configuration. This enables integration
with any external identity provider.

### Lambda invocation flow

```text
1. Client connects to Transfer Family server (SFTP/FTPS/FTP)
2. Client presents credentials (SSH key or password)
3. Transfer Family invokes the Lambda function with:
   {
     "username": "alice",
     "password": "secret123",    // or "protocolData" for SSH
     "serverId": "s-xxx",
     "sourceIp": "10.0.1.5"
   }
4. Lambda validates credentials (against Okta, Auth0, DB, etc.)
5. Lambda returns user configuration:
   {
     "Role": "arn:aws:iam::xxx:role/TransferFamilyS3",
     "HomeDirectoryType": "LOGICAL",
     "HomeDirectoryDetails": "[{\"Entry\":\"/\",\"Target\":\"/bucket/home/alice\"}]",
     "Policy": "<session policy JSON>"
   }
6. Transfer Family applies the configuration for the session
```

### Lambda response format

The Lambda function MUST return a JSON object with these fields:

| Field | Required | Description |
|---|---|---|
| `Role` | Yes | IAM role ARN to assume for the user |
| `HomeDirectoryType` | Yes | `PATH` or `LOGICAL` |
| `HomeDirectory` | If PATH | Direct S3 path (e.g., `/bucket/home/alice`) |
| `HomeDirectoryDetails` | If LOGICAL | JSON string of entry/target mappings |
| `Policy` | Recommended | Session policy JSON for per-user S3 scoping |
| `PublicKeys` | Optional | SSH public keys for the user |

### Lambda IAM permissions

The Lambda function's execution role needs `lambda:InvokeFunction`
permission for Transfer Family:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "transfer.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

## Endpoint types

### PUBLIC endpoint

The server is accessible from the internet via a public DNS name.
Transfer Family assigns the endpoint automatically.

```bash
aws transfer create-server --protocols SFTP --endpoint-type PUBLIC
```

**Use case:** B2B partner access where partners connect from external
networks. Restrict access by IP in the security group if partner IPs
are known.

### VPC endpoint (NLB-based)

The server is accessible within a VPC via an NLB. Full NLB control
(cross-zone, DNS, health checks).

```bash
aws transfer create-server \
  --protocols SFTP \
  --endpoint-type VPC \
  --endpoint-details \
    VpcId=vpc-aaa11122,\
    SubnetIds=subnet-aaa,subnet-bbb,\
    SecurityGroupIds=sg-sftp
```

**Cost:** NLB hourly charge + data processing charges, in addition to
the Transfer Family server charge.

### VPC_ENDPOINT (PrivateLink)

The server is accessible within a VPC via AWS PrivateLink. No NLB is
provisioned. A VPC endpoint network interface is placed in each
specified subnet.

```bash
aws transfer create-server \
  --protocols SFTP \
  --endpoint-type VPC_ENDPOINT \
  --endpoint-details \
    VpcId=vpc-aaa11122,\
    SubnetIds=subnet-aaa,subnet-bbb,\
    SecurityGroupIds=sg-sftp
```

**Advantages over VPC:**
- No NLB cost (PrivateLink only charges per-hour for the endpoint)
- Simpler networking (no NLB health checks or cross-zone config)
- Accessible via VPC peering, Transit Gateway, VPN, Direct Connect

**Requirement:** the VPC must have DNS resolution and DNS hostnames
enabled.

## Security group configuration

For VPC and VPC_ENDPOINT types, the security group controls inbound
traffic to the Transfer Family endpoint.

| Protocol | Port | Direction | Source |
|---|---|---|---|
| SFTP | TCP 22 | Inbound | Client CIDR range |
| FTPS | TCP 990 | Inbound | Client CIDR range |
| FTP | TCP 21 | Inbound | Client CIDR range |
| FTP passive | TCP 8192-8200 | Inbound | Client CIDR range |

**Best practice:** restrict the source CIDR to known client ranges.
Do NOT use `0.0.0.0/0` for VPC/VPC_ENDPOINT types.

## Terraform examples

```hcl
# SFTP server with VPC_ENDPOINT and custom Lambda IDP
resource "aws_transfer_server" "sftp" {
  protocols                  = ["SFTP"]
  endpoint_type              = "VPC_ENDPOINT"
  identity_provider_type     = "LAMBDA"
  logging_role               = aws_iam_role.logging.arn
  invocation_role            = aws_iam_role.invocation.arn
  function                   = aws_lambda_function.idp.arn

  endpoint_details {
    vpc_id             = data.aws_vpc.main.id
    subnet_ids         = data.aws_subnets.private.ids
    security_group_ids = [aws_security_group.sftp.id]
  }

  tags = {
    Environment = "production"
    App         = "file-landing-zone"
  }
}

# Security group for the SFTP endpoint
resource "aws_security_group" "sftp" {
  name        = "sftp-internal"
  description = "Allow SFTP from internal subnets"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}
```
