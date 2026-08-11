---
name: transfer-family-workflow-deployer
description: >-
  Provisions AWS Transfer Family servers and managed workflows with
  production defaults: SFTP/FTPS/FTP protocol, identity provider
  (service-managed, AWS Directory Service, custom Lambda), endpoint
  type (PUBLIC, VPC, VPC_ENDPOINT), security groups and subnets,
  Route 53 hosted zone DNS, user home directory mapping (logical vs
  physical), S3 access via IAM role and session policy for per-user
  scoping, AS2 connectors for trading partner exchange, Managed
  Workflow with Step Functions for file processing, structured JSON
  logging, server host key, trusted host keys. Emits a
  READY_TO_DEPLOY checklist with verification commands. Use when
  creating a Transfer Family SFTP server, configuring custom Lambda
  authentication, setting up VPC endpoint for private SFTP, or
  deploying managed workflows. Triggers: create transfer family sftp
  server, transfer family custom lambda identity, transfer family vpc
  endpoint, transfer family managed workflow, transfer family as2
  connector, sftp user session policy.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with transfer
  access, plus iam, s3, ec2, route53, and lambda access for custom
  identity providers and VPC endpoints. Works with Terraform
  aws_transfer_server / aws_transfer_user /
  aws_transfer_workflow resources and CloudFormation
  AWS::Transfer::Server / AWS::Transfer::User /
  AWS::Transfer::Workflow templates.
keywords:
  - aws
  - transfer family
  - sftp
  - ftps
  - ftp
  - storage
  - cloudops
  - deploy
  - provisioning
  - managed file transfer
  - mft
  - session policy
  - as2
  - managed workflow
  - vpc endpoint
  - identity provider
  - custom lambda
  - service managed
  - home directory
  - host key
tags:
  - aws
  - transfer-family
  - sftp
  - cloudops
  - deploy
  - storage
  - provisioning
  - managed-file-transfer
  - session-policy
  - as2
  - managed-workflow
  - vpc-endpoint
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Storage
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - transfer-family
    - sftp
    - cloudops
    - deploy
    - storage
    - provisioning
    - managed-file-transfer
    - session-policy
    - as2
    - managed-workflow
    - vpc-endpoint
  dependencies:
    - aws-orchestrator
  keywords:
    - create transfer family sftp server
    - transfer family custom lambda identity
    - transfer family vpc endpoint
    - transfer family managed workflow
    - transfer family as2 connector
    - sftp user session policy
    - transfer family hosted zone route53
  when_to_use: >-
    Invoke when the user wants to create or configure an AWS Transfer
    Family server (SFTP, FTPS, FTP), set up identity provider
    (service-managed, Directory Service, custom Lambda), configure VPC
    or VPC_ENDPOINT for private SFTP access, manage user home directory
    mapping, configure per-user S3 access via session policy, deploy
    managed workflows for file processing, or set up AS2 connectors
    for B2B file exchange. Do NOT invoke for AWS DataSync (use
    datasync skills), S3 direct access patterns, or Storage Gateway.
---

# Transfer Family Workflow Deployer

An AWS CloudOps agent skill that provisions AWS Transfer Family
servers and managed workflows with correct defaults. The skill walks
the operator through protocol selection (SFTP/FTPS/FTP), identity
provider choice (service-managed, Directory Service, custom Lambda),
endpoint type (PUBLIC, VPC, VPC_ENDPOINT), VPC and security group
configuration, Route 53 hosted zone DNS, user home directory mapping
(logical vs physical), per-user S3 access via IAM role and session
policy, AS2 connectors for trading partner exchange, managed workflow
with Step Functions for file landing zone automation, structured JSON
logging, CloudWatch metrics and throttling, server host key generation,
and trusted host keys for partner verification, captures architecture
decisions, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create Transfer Family SFTP server, Transfer Family custom Lambda
identity, Transfer Family VPC endpoint, Transfer Family managed
workflow, Transfer Family AS2 connector, SFTP user session policy,
Transfer Family hosted zone Route 53, SFTP home directory mapping,
Transfer Family server host key, Transfer Family trusted host keys.

## STRICT output contract

When this skill is invoked with a Transfer-Family-provisioning request
(create a server, configure identity provider, set up VPC endpoint,
deploy managed workflow, configure AS2 connector, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `TRANSFER_FAMILY:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Server model and protocols | Core Transfer Family model |
| Step 2 — Identity provider (service-managed, DS, Lambda) | Authentication |
| Step 3 — Endpoint type (PUBLIC, VPC, VPC_ENDPOINT) | Network placement |
| Step 4 — VPC, subnets, security groups | Private connectivity |
| Step 5 — Route 53 hosted zone DNS | Custom hostname |
| Step 6 — User home directory mapping | S3 path mapping |
| Step 7 — IAM role and session policy | Per-user S3 scoping |
| Step 8 — Server host key and trusted host keys | SSH key management |
| Step 9 — AS2 connectors | B2B trading partner exchange |
| Step 10 — Managed workflows | File landing zone automation |
| Step 11 — Structured JSON logging and CloudWatch | Observability |
| Step 12 — Throttling and limits | Performance |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/identity-providers-and-endpoints.md | IDP + endpoint detail |
| references/managed-workflows-and-as2.md | Workflow + AS2 detail |

## Mindset

**One-line takeaway:** AWS Transfer Family is a managed SFTP/FTPS/FTP
server that bridges legacy file transfer protocols with AWS S3 (and
EFS). Users authenticate via service-managed SSH keys, AWS Directory
Service, or a custom Lambda identity provider. Each user is scoped to
specific S3 paths via a session policy applied at connection time.
Managed workflows automate pre/post file processing via Step Functions.

Three misconceptions dominate Transfer Family misdesign at provisioning
time:

- **"Public endpoint with service-managed auth is fine for production."**
  For B2B or internal file transfers, a PUBLIC endpoint exposes the
  SFTP server to the entire internet. VPC or VPC_ENDPOINT provides
  private connectivity. Combined with a custom Lambda identity
  provider, this gives enterprise-grade access control including MFA,
  credential brokering, and audit trails.

- **"The IAM role's S3 permissions are sufficient."** They are not. The
  IAM role defines the MAXIMUM permissions, but the session policy
  defines the EFFECTIVE per-user scope. A user with an IAM role that
  grants `s3:*` on `*` but a session policy that restricts to
  `s3:GetObject` on `my-bucket/home/alice/*` can only read their own
  directory. Without a session policy, the user inherits the full IAM
  role permissions — a security risk.

- **"Managed workflows are optional post-processing."** They are the
  core value of a file landing zone. Without a managed workflow, files
  land in S3 and sit there. A managed workflow with Step Functions can
  trigger virus scanning, format validation, transformation, and
  routing on every upload — turning SFTP from a passive file store
  into an active data pipeline.

## Configuration dependency graph (novel heuristic)

Transfer Family configurations are NOT independent. The endpoint type
determines whether VPC subnets and security groups are required. The
identity provider determines whether a Lambda function needs to be
deployed. The session policy must reference S3 paths that match the
user's home directory mapping. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Transfer server | IAM role for logging; S3 bucket exists | server creation succeeds but USERS cannot connect until identity provider is configured | SFTP/FTPS/FTP endpoint |
| Identity provider | Lambda function (for custom); Directory Service (for managed DS) | service-managed users created via `create-user` but cannot authenticate without SSH key upload | user authentication |
| Endpoint type — VPC | VPC ID, subnet IDs, security group IDs | VPC endpoint requires a VPC with DNS resolution enabled; NLB is provisioned automatically | private SFTP connectivity |
| Endpoint type — VPC_ENDPOINT | VPC ID, subnet IDs, security group IDs | uses PrivateLink (no NLB); clients connect from within the VPC or via peering/TGW | private SFTP via PrivateLink |
| User home directory | S3 bucket exists; logical mapping if `HomeDirectoryType=LOGICAL` | physical mapping uses `HomeDirectory=/bucket/path`; logical mapping uses `HomeDirectoryDetails` with entry/ target pairs | per-user S3 path |
| IAM role (user) | trust policy allowing `transfer.amazonaws.com`; S3 permissions | without S3 permissions, user authenticates but CANNOT read/write files | S3 access for the user |
| Session policy | IAM role attached; policy scopes S3 to user's home directory | WITHOUT session policy, user inherits FULL IAM role permissions — security risk | per-user S3 scoping |
| Server host key | generated automatically or uploaded via `create-server` with `host-key` | SSH clients see a host key warning until trusted host key is distributed | SSH host verification |
| AS2 connector | trading partner certificate; local profile (private key) | AS2 requires mutual certificate exchange; without partner's public cert, messages cannot be encrypted/verified | B2B AS2 file exchange |
| Managed workflow | S3 bucket for file landing; Step Functions state machine | workflow steps run AFTER the file is uploaded; pre-processing steps run before the file is available to the user | automated file processing pipeline |

**The session-policy row is the one a baseline model misses.** Creating
a user without a session policy means the user inherits the full IAM
role permissions. If the IAM role grants broad S3 access, every SFTP
user can access every bucket. The session policy is the mechanism that
scopes each user to their own home directory. The endpoint-type row is
another commonly misunderstood configuration — operators default to
PUBLIC without considering that VPC_ENDPOINT provides private SFTP with
no internet exposure.

**Cross-dependency gotchas:**
- The IAM role's trust policy MUST allow `transfer.amazonaws.com` as
  principal. Without it, Transfer Family cannot assume the role on
  behalf of the connecting user.
- Session policy and IAM role permissions are INTERSECTED, not unioned.
  The effective permissions are the INTERSECTION of the session policy
  and the IAM role. If either is restrictive, the effective permission
  is restrictive.
- VPC_ENDPOINT type uses AWS PrivateLink. Clients connect from within
  the VPC or via VPC peering / Transit Gateway. No NLB is provisioned.
  VPC type provisions an NLB inside the VPC.
- AS2 connectors require certificate exchange. You need the trading
  partner's public certificate AND your own private key pair.
- Managed workflow steps are executed via Step Functions. The workflow
  must be deployed and the Transfer server must reference the workflow
  ID in its configuration.

## Expert heuristic: session policy for per-user S3 scoping

A baseline model says "attach an IAM role with S3 permissions." The
correct heuristic recognizes that the session policy is the per-user
scoping mechanism.

```text
Per-user S3 scoping model:
  IAM role (assumed by Transfer Family on behalf of the user):
    ├── Defines MAXIMUM permissions (e.g., s3:GetObject, s3:PutObject)
    └── Attached to each user via create-user --role

  Session policy (applied at connection time):
    ├── Scopes the IAM role to specific S3 paths
    ├── Effective permissions = IAM role INTERSECT session policy
    └── Without session policy → user gets FULL IAM role permissions (RISK)

  Example:
    IAM role: s3:GetObject, s3:PutObject on all buckets
    Session policy: s3:GetObject, s3:PutObject on my-bucket/home/alice/*
    Effective: s3:GetObject, s3:PutObject on my-bucket/home/alice/*

  Without session policy:
    Effective: s3:GetObject, s3:PutObject on ALL buckets (SECURITY RISK)
```

**Key implication:** ALWAYS attach a session policy to every Transfer
Family user. The session policy is the only mechanism that scopes
each user to their own home directory. Without it, a user can access
any S3 path the IAM role permits.

## Expert heuristic: managed workflow for file landing zone automation

A managed workflow turns SFTP from a passive file store into an active
data pipeline. Every file upload triggers a Step Functions execution.

```text
Managed workflow pipeline (per file upload):
  1. File arrives via SFTP → lands in S3 (home directory)
  2. Transfer Family triggers the managed workflow
  3. Step Functions executes the workflow steps:
     ├── Pre-processing (optional): virus scan, format validation
     │   → if fails: quarantine file, notify user
     │   → if passes: continue
     4. File is available in S3
     5. Post-processing: transform, route, trigger downstream
        ├── Copy to data lake bucket
        ├── Trigger Lambda for ETL
        ├── Send SNS notification
        └── Move to archive bucket

  Workflow definition (JSON):
    Steps:
      - Type: COPY | DELETE | TAG | CUSTOM
      - Destination: s3://data-lake/processed/${originalName}
      - OnException: send SNS, retry 3x
```

**Key implication:** managed workflows are the mechanism for building
a file landing zone on Transfer Family. Without a workflow, files land
in S3 and require manual intervention or a separate event-driven
pipeline. With a workflow, the entire processing chain is automated
and visible in Step Functions execution history.

## Expert heuristic: VPC endpoint for private SFTP

A baseline model uses a PUBLIC endpoint. The correct heuristic
recognizes that VPC_ENDPOINT provides private SFTP with zero internet
exposure.

```text
Endpoint type decision tree:
  ├── B2B with external partners → PUBLIC endpoint (internet-facing)
  │     + service-managed or custom Lambda IDP
  │     + restrict by IP in security group (if partner IPs are known)
  ├── Internal users, within VPC → VPC_ENDPOINT (PrivateLink)
  │     + no internet exposure; clients connect via VPC internals
  │     + requires VPC with DNS resolution
  │     + accessible via VPC peering, TGW, VPN, DX
  └── Internal users, need NLB features → VPC (NLB-based)
        + full NLB control (cross-zone, DNS, health checks)
        + more expensive (NLB hourly + data processing)
        + use when you need NLB-specific features

Key: VPC_ENDPOINT is preferred for private SFTP because it uses
PrivateLink (no NLB cost) and provides a private IP within the VPC.
```

**Key implication:** VPC_ENDPOINT is the recommended endpoint type for
internal file transfers. It provides a private SFTP endpoint without
exposing the server to the internet and without the cost of an NLB.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| S3 bucket exists | Users need an S3 bucket for home directory | `aws s3 ls s3://<bucket>` |
| IAM role for Transfer Family | Server needs a logging role; users need an access role | `aws iam get-role --role-name <name>` |
| IAM role trust policy | Must allow `transfer.amazonaws.com` as principal | Check trust policy document |
| VPC and subnets (for VPC/VPC_ENDPOINT) | Private endpoints need VPC infrastructure | `aws ec2 describe-subnets` |
| Security group (for VPC/VPC_ENDPOINT) | Controls inbound traffic to the endpoint | `aws ec2 describe-security-groups` |
| Route 53 hosted zone (for custom DNS) | Optional: custom hostname for the server | `aws route53 list-hosted-zones` |
| Lambda function (for custom IDP) | Custom identity provider needs a Lambda function | `aws lambda get-function --function-name <name>` |
| SSL/TLS certificate (for FTPS) | FTPS requires a certificate | `aws acm describe-certificate --certificate-arn <arn>` |
| Trading partner certificate (for AS2) | AS2 requires the partner's public certificate | Confirm certificate availability |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Server model and protocols

Transfer Family provides managed file transfer servers supporting
SFTP, FTPS, and FTP protocols.

| Protocol | Port | Encryption | Authentication | Use case |
|---|---|---|---|---|
| SFTP | 22 | SSH-based | SSH key (service-managed), password (DS/Lambda) | B2B, partner integration |
| FTPS | 990 | TLS | Password (DS/Lambda) | Compliance (explicit TLS) |
| FTP | 21 | None | Password (DS/Lambda) | Legacy (VPC-only) |

**FTP requires VPC or VPC_ENDPOINT** — it is NOT available on PUBLIC
endpoints (no encryption). FTPS requires an ACM or imported certificate.

A single server supports ONE protocol family. For SFTP + FTPS, create
two servers.

## Step 2 — Identity provider (service-managed, DS, Lambda)

| Provider | How it works | Best for |
|---|---|---|
| Service-managed | SSH keys stored in Transfer Family | Simple SFTP with known users |
| AWS Directory Service | Integrates with AWS Managed AD | Enterprise AD integration |
| Custom (Lambda) | Lambda function validates credentials | Custom auth, MFA, external IdP |

**Service-managed:** store each user's public SSH key via `create-user`
with `SshPublicKeys`. Transfer Family validates the SSH key against the
connecting user.

**Custom Lambda:** deploy a Lambda function that receives the username
and password (or SSH key) and returns the user's S3 home directory, IAM
role, and session policy. This enables integration with any external
identity provider (Okta, Auth0, Active Directory via LDAP, database
lookup).

## Step 3 — Endpoint type (PUBLIC, VPC, VPC_ENDPOINT)

| Type | Accessibility | Cost | Network | Use case |
|---|---|---|---|---|
| PUBLIC | Internet-facing | Server only | Direct internet | B2B partner access |
| VPC | VPC-internal via NLB | Server + NLB | NLB in your VPC | Internal with NLB features |
| VPC_ENDPOINT | VPC-internal via PrivateLink | Server only | PrivateLink endpoint | Private SFTP (recommended) |

**VPC_ENDPOINT** uses AWS PrivateLink. No NLB is provisioned. The
server is accessible via a private IP in your VPC. Clients connect
from within the VPC, via VPC peering, Transit Gateway, VPN, or Direct
Connect.

## Step 4 — VPC, subnets, security groups

For VPC and VPC_ENDPOINT types, specify subnets and security groups:

```bash
aws transfer create-server \
  --protocols SFTP \
  --endpoint-type VPC_ENDPOINT \
  --endpoint-details \
    VpcId=vpc-aaa11122,\
    SubnetIds=subnet-aaa,subnet-bbb,\
    SecurityGroupIds=sg-sftp
```

**Security group rules:** allow inbound TCP 22 (SFTP) from the
expected client CIDR ranges. For VPC_ENDPOINT, the security group
is attached to the VPC endpoint network interface.

## Step 5 — Route 53 hosted zone DNS

To use a custom hostname (e.g., `sftp.example.com`), create a Route 53
record pointing to the server endpoint:

```bash
# Get the server endpoint
SERVER_ENDPOINT=$(aws transfer describe-server --server-id s-xxx \
  --query 'Server.EndpointDetails.Address' --output text)

# Create a CNAME record in Route 53
aws route53 change-resource-record-sets \
  --hosted-zone-id Z111111XXXX \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "sftp.example.com",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [{"Value": "'"$SERVER_ENDPOINT"'"}]
      }
    }]
  }'
```

## Step 6 — User home directory mapping

| Mapping type | How it works | Flexibility |
|---|---|---|
| Physical (`HomeDirectoryType=PATH`) | Direct S3 path: `/bucket/home/alice` | One directory per user |
| Logical (`HomeDirectoryType=LOGICAL`) | Virtual paths mapped to real S3 paths | Multiple directories, chroot-like |

**Logical mapping** uses `HomeDirectoryDetails` to map virtual paths
to real S3 paths:

```bash
aws transfer create-user \
  --server-id s-xxx \
  --user-name alice \
  --role arn:aws:iam::123456789012:role/TransferFamilyS3 \
  --home-directory-type LOGICAL \
  --home-directory-mappings \
    Entry=/uploads,Target=/my-bucket/home/alice/uploads \
    Entry=/downloads,Target=/shared-bucket/distributions
```

Alice sees `/uploads` and `/downloads` as top-level directories, but
they map to different S3 buckets.

## Step 7 — IAM role and session policy

The IAM role is assumed BY Transfer Family on behalf of the user. The
session policy scopes the role to the user's home directory.

**IAM role trust policy:**
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

**Session policy (per-user S3 scoping):**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:ListBucket"],
    "Resource": "arn:aws:s3:::my-bucket",
    "Condition": {
      "StringLike": {"s3:prefix": ["home/alice/*"]}
    }
  }, {
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject"],
    "Resource": "arn:aws:s3:::my-bucket/home/alice/*"
  }]
}
```

```bash
aws transfer create-user \
  --server-id s-xxx \
  --user-name alice \
  --role arn:aws:iam::123456789012:role/TransferFamilyS3 \
  --session-policy file://session-policy-alice.json
```

**Critical:** the session policy INTERSECTS with the IAM role. The
effective permissions are the intersection of both. If the IAM role
does not grant S3 access, the session policy cannot add it.

## Step 8 — Server host key and trusted host keys

The server host key identifies the Transfer Family server to SSH
clients. Transfer Family generates one automatically, but you can
upload a custom host key for brand consistency or compliance.

```bash
# Create server with a custom host key
aws transfer create-server \
  --protocols SFTP \
  --host-key file://server_host_key_rsa
```

**Trusted host keys** are used by clients to verify the server. When a
client connects, SSH compares the server's host key against its
known_hosts entry. Distribute the host key to clients via a secure channel.

## Step 9 — AS2 connectors

AS2 (Applicability Statement 2) is a B2B file transfer protocol for
EDI (Electronic Data Interchange) trading partner exchange.

```bash
aws transfer create-connector \
  --url "https://partner.example.com/as2" \
  --as2-config \
    Compression=ZLIB,EncryptionAlgorithm=AES256_CBC,\
    SigningAlgorithm=SHA256,MdnResponse=SYNC,\
    LocalProfileId=local-profile-xxx,PartnerProfileId=partner-profile-yyy
```

AS2 requires certificate exchange: you need the partner's public
certificate (for encryption) and your own private key (for signing).
Certificates are managed via Transfer Family profiles.

## Step 10 — Managed workflows

Managed workflows automate file processing via Step Functions. Each
file upload triggers the workflow.

```bash
# Create a managed workflow
aws transfer create-workflow \
  --description "File landing zone pipeline" \
  --steps \
    Type=COPY,\
    CopyStepDetails={DestinationFileLocation={Bucket=processed-data,Key=landing/},Name=CopyToDataLake},\
    Type=TAG,\
    TagStepDetails={Tags=[{Key=Status,Value=Processed}]} \
  --on-exception-steps \
    Type=TAG,\
    TagStepDetails={Tags=[{Key=Status,Value=Failed}]}
```

Attach the workflow to the Transfer server:

```bash
aws transfer update-server \
  --server-id s-xxx \
  --workflow-id w-xxx
```

Every file upload now triggers the workflow: copy to the data lake,
tag as processed, and on exception tag as failed.

## Step 11 — Structured JSON logging and CloudWatch

Transfer Family supports structured JSON logging to CloudWatch Logs.
Each connection, authentication, and file transfer is logged.

```bash
# Enable structured logging
aws transfer create-server \
  --protocols SFTP \
  --logging-role arn:aws:iam::123456789012:role/TransferFamilyLogging \
  --structured-log-destinations arn:aws:logs:us-east-1:123456789012:log-group:/aws/transfer/sftp
```

Structured logs include connection timestamp, client IP, username,
authentication result, file transfer details, and session duration.

## Step 12 — Throttling and limits

| Limit | Default | Adjustable |
|---|---|---|
| Files per second (per server) | 100 | Yes (support ticket) |
| Concurrent connections | 10,000 | Yes |
| Users per server | 10,000 (service-managed) | Yes |
| File size | 5 GB max (S3 limit) | No |
| Workflows per server | 1 | No |

CloudWatch metrics (`FilesIn`, `FilesOut`, `BytesIn`, `BytesOut`)
provide throughput visibility.

## Step 13 — Recent features

**Recent AWS features (2023-2026):**

- **Managed Workflows GA (2023-2024):** Step Functions-based managed
  workflows for automated pre/post file processing. Configurable steps:
  COPY, DELETE, TAG, CUSTOM (Lambda). On-exception steps for error
  handling.

- **AS2 Connectors GA (2023-2024):** B2B AS2 protocol support for
  EDI trading partner exchange. Certificate-based encryption and
  signing. Message Disposition Notifications (MDN) for delivery
  confirmation.

- **Structured JSON Logging (2023-2024):** Structured JSON logs to
  CloudWatch Logs with per-connection, per-file, and per-session
  details. Enables CloudWatch Logs Insights queries for audit and
  troubleshooting.

- **VPC_ENDPOINT Support (2023-2024):** PrivateLink-based VPC endpoint
  for private SFTP without NLB cost. Connect via VPC peering, TGW, VPN,
  or Direct Connect.

- **EFS Backing Storage (2023-2024):** Transfer Family now supports
  EFS as backing storage in addition to S3. Users can be mapped to EFS
  access points for file-system-based workflows.

- **Directory Service Integration (2024-2025):** Enhanced AWS Directory
  Service integration with automatic user provisioning and group-based
  home directory mapping.

- **Web App (2024-2025):** Managed web-based file browser for Transfer
  Family users, providing a GUI alternative to SFTP clients.

## NEVER do these things

1. **NEVER create a Transfer Family user without a session policy.**
   Without a session policy, the user inherits the FULL IAM role
   permissions. If the role grants broad S3 access, every SFTP user
   can access every bucket. ALWAYS attach a session policy that scopes
   the user to their home directory.

2. **NEVER use a PUBLIC endpoint for internal file transfers.** PUBLIC
   endpoints expose the SFTP server to the entire internet. For
   internal transfers, use VPC_ENDPOINT (PrivateLink, recommended) or
   VPC (NLB-based).

3. **NEVER assume the IAM role alone provides per-user scoping.** The
   IAM role defines MAXIMUM permissions. The session policy provides
   EFFECTIVE per-user scoping. Both are required.

4. **NEVER deploy an SFTP server without a server host key strategy.**
   SSH clients will see a host key warning on first connection if the
   key is not distributed via a trusted channel. Upload a custom host
   key for brand consistency and distribute it to clients.

5. **NEVER forget the IAM role trust policy.** The role assumed by
   Transfer Family on behalf of users MUST have a trust policy allowing
   `transfer.amazonaws.com`. Without it, the role cannot be assumed and
   users cannot connect.

6. **NEVER create a managed workflow without on-exception steps.** If a
   workflow step fails and there are no on-exception steps, the file is
   left in an indeterminate state. Always define cleanup or notification
   steps for exceptions.

7. **NEVER use FTP on a PUBLIC endpoint.** FTP sends credentials in
   plaintext. FTP is ONLY available on VPC and VPC_ENDPOINT types. For
   external partners, use SFTP or FTPS.

8. **NEVER assume logical home directory mapping is chroot.** Logical
   mapping provides virtual paths but does NOT prevent a user from
   navigating to other paths if the session policy permits. The session
   policy is the security boundary, not the home directory mapping.

9. **NEVER deploy AS2 connectors without certificate verification.** AS2
   requires mutual certificate exchange. Verify the trading partner's
   certificate fingerprint before configuring the connector.

10. **NEVER ignore Transfer Family CloudWatch metrics.** Monitor
    `FilesIn`, `FilesOut`, `BytesIn`, `BytesOut`, and authentication
    failure rates. Sudden spikes or drops indicate issues with partner
    connectivity or automated processes.

## Output format

```text
TRANSFER_FAMILY: <server-id> (<protocols>) — <endpoint-type>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Server: <server-id> (<protocol: SFTP|FTPS|FTP>)
  [✓|✗] Endpoint type: PUBLIC | VPC | VPC_ENDPOINT
  [✓|✗] Identity provider: Service-managed | Directory Service | Custom Lambda
  [✓|✗] VPC: <vpc-id> (subnets: <subnet-list>) | N/A (PUBLIC)
  [✓|✗] Security groups: <sg-list> | N/A (PUBLIC)
  [✓|✗] Route 53: <hostname> → <endpoint> | N/A
  [✓|✗] S3 bucket: <bucket-name>
  [✓|✗] Users: <user-list> (home directory: <mapping-type>)
  [✓|✗] IAM role: <role-name> (trust: transfer.amazonaws.com)
  [✓|✗] Session policy: attached per-user (S3 scoped) | MISSING (RISK)
  [✓|✗] Server host key: custom | auto-generated
  [✓|✗] Managed workflow: <workflow-id> (<steps>) | none
  [✓|✗] AS2 connector: <connector-id> (<partner>) | N/A
  [✓|✗] Structured logging: CloudWatch <log-group> | disabled
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws transfer describe-server --server-id <server-id>
  aws transfer list-users --server-id <server-id>
  aws transfer describe-workflow --workflow-id <workflow-id>
```

### Worked example — SFTP with VPC_ENDPOINT, custom Lambda, and managed workflow

```text
TRANSFER_FAMILY: s-abc123 (SFTP) — VPC_ENDPOINT
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Server: s-abc123 (SFTP)
  [✓] Endpoint type: VPC_ENDPOINT (PrivateLink)
  [✓] Identity provider: Custom Lambda (transfer-idp-auth)
  [✓] VPC: vpc-aaa11122 (subnets: subnet-aaa, subnet-bbb)
  [✓] Security groups: sg-sftp-internal
  [✓] Route 53: sftp.internal.example.com → vpce-xxx
  [✓] S3 bucket: file-landing-zone
  [✓] Users: alice, bob, carol (home directory: LOGICAL)
  [✓] IAM role: TransferFamilyS3Access (trust: transfer.amazonaws.com)
  [✓] Session policy: attached per-user (scoped to /home/<user>/*)
  [✓] Server host key: custom (RSA 4096)
  [✓] Managed workflow: w-def456 (COPY → TAG → CUSTOM Lambda scan)
  [✓] AS2 connector: N/A
  [✓] Structured logging: CloudWatch /aws/transfer/sftp
  [✓] Tags: Environment=production, App=file-landing-zone
VERIFICATION_COMMANDS:
  aws transfer describe-server --server-id s-abc123
  aws transfer list-users --server-id s-abc123
  aws transfer describe-workflow --workflow-id w-def456
```

## Error handling

- **User authenticates but cannot read/write files:** check IAM role
  S3 permissions AND session policy (effective = intersection).
- **Connection timeout on VPC_ENDPOINT:** verify security group allows
  TCP 22 from client subnet. Check VPC DNS resolution.
- **Managed workflow not triggering:** verify workflow attached via
  `describe-server`. Check Step Functions execution history.
- **AS2 delivery failure:** verify partner certificate validity and
  connector URL. Check MDN status.
- **Custom Lambda auth failure:** check Lambda CloudWatch Logs. Verify
  response format (home directory, IAM role, session policy).

## Domain

AWS CloudOps / AWS Transfer Family Managed File Transfer & Automation.

## AWS documentation

- **Transfer Family User Guide** — https://docs.aws.amazon.com/transfer/latest/userguide/what-is-aws-transfer.html
- **Creating a server** — https://docs.aws.amazon.com/transfer/latest/userguide/create-server.html
- **Identity providers** — https://docs.aws.amazon.com/transfer/latest/userguide/authenticating-users.html
- **Custom Lambda IDP** — https://docs.aws.amazon.com/transfer/latest/userguide/configuring-custom-idp.html
- **Session policies** — https://docs.aws.amazon.com/transfer/latest/userguide/session-policy.html
- **Managed workflows** — https://docs.aws.amazon.com/transfer/latest/userguide/create-workflow.html
- **AS2 connectors** — https://docs.aws.amazon.com/transfer/latest/userguide/as2.html
- **VPC endpoints** — https://docs.aws.amazon.com/transfer/latest/userguide/configuring-endpoints.html
- **Structured logging** — https://docs.aws.amazon.com/transfer/latest/userguide/structured-logging.html
