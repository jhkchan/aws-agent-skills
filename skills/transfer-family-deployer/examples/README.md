# End-to-end usage scenario: transfer-family-deployer

A walkthrough showing the skill creating a Service Managed SFTP server
with per-user session policies, then extending it with a custom API
Gateway Lambda IdP, and finally blocking an attempt to enable plain
FTP on a public endpoint. Each path includes pre-checks, CONFIRM gate,
and post-verification.

## Input (user prompt)

> Create a Service Managed SFTP server "prod-sftp-inbox" in us-east-1
> with S3 backend and per-user session policies for alice and bob.
> Then build a custom IdP version on VPC endpoint with FTPS. Finally,
> the legacy team wants plain FTP on the public endpoint — block that.

```json
{
  "Operation": "create",
  "Server description": "prod-sftp-inbox",
  "Region": "us-east-1",
  "Account": "111111111111",
  "Protocols": ["SFTP"],
  "EndpointType": "PUBLIC",
  "IdentityProviderType": "SERVICE_MANAGED",
  "Storage backend": "S3 bucket prod-sftp-inbox",
  "LoggingRole": "arn:aws:iam::111111111111:role/TransferLoggingRole",
  "Users": [
    {"UserName": "alice", "SSHPublicKey": "ssh-rsa AAAAB3...", "Role": "arn:aws:iam::111111111111:role/TransferUserS3Role", "HomeDirectory": "/prod-sftp-inbox/alice"},
    {"UserName": "bob", "SSHPublicKey": "ssh-rsa AAAAB3...", "Role": "arn:aws:iam::111111111111:role/TransferUserS3Role", "HomeDirectory": "/prod-sftp-inbox/bob"}
  ]
}
```

## Skill output — create Service Managed SFTP server

```text
SERVER: prod-sftp-inbox
VERDICT: READY_TO_DEPLOY
TARGET: prod-sftp-inbox
PRE_CHECKS:
  - [PASS] Protocols valid: SFTP
  - [PASS] Endpoint type: PUBLIC (acceptable for SFTP; VPC preferred for partner B2B)
  - [PASS] Identity provider: SERVICE_MANAGED
  - [PASS] S3 bucket prod-sftp-inbox exists in us-east-1
  - [PASS] IAM role TransferUserS3Role trusts transfer.amazonaws.com with SourceAccount=111111111111
  - [PASS] IAM role has s3:ListBucket, s3:GetObject, s3:PutObject on bucket
  - [PASS] Logging role TransferLoggingRole resolves with logs:* permissions
  - [PASS] Operator principal holds transfer:CreateServer and iam:PassRole
STEPS:
  1. CONFIRM: About to create-server prod-sftp-inbox in account
     111111111111 region us-east-1. This will CREATE a new Transfer
     Family server with SFTP protocol, Service Managed IdP, and
     CloudWatch logging. Proceed? (yes/no)
  2. aws transfer create-server --description prod-sftp-inbox
     --protocols SFTP --endpoint-type PUBLIC
     --identity-provider-type SERVICE_MANAGED
     --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole
     --tags Key=Environment,Value=prod
  3. aws transfer create-user --server-id <returned-id> --user-name alice
     --role arn:aws:iam::111111111111:role/TransferUserS3Role
     --home-directory /prod-sftp-inbox/alice
     --ssh-public-key-body "ssh-rsa AAAAB3..."
     --policy '{session policy scoping alice to /prod-sftp-inbox/alice/*}'
  4. aws transfer create-user --server-id <returned-id> --user-name bob
     --role arn:aws:iam::111111111111:role/TransferUserS3Role
     --home-directory /prod-sftp-inbox/bob
     --ssh-public-key-body "ssh-rsa AAAAB3..."
     --policy '{session policy scoping bob to /prod-sftp-inbox/bob/*}'
POST_VERIFY:
  - (pending execution)
  - describe-server returns State=ONLINE
  - describe-user returns alice and bob with their SSH keys, roles,
    home directories, and session policies
PROTOCOLS: SFTP
ENDPOINT: PUBLIC
IDP: ServiceManaged
STORAGE: S3 (bucket: prod-sftp-inbox)
SESSION_POLICY_SCOPE: per-user home prefix (alice: /alice/*, bob: /bob/*)
WORKFLOWS: 0 attached
NOTES:
  - PUBLIC endpoint exposes SFTP to the internet — VPC endpoint preferred
    for partner B2B.
  - Session policy is the effective security boundary — without it each
    user inherits the full IAM role scope (the entire bucket).
  - SSH keys rotate per user via delete-ssh-public-key + create-ssh-public-key.
  - Tags Environment=prod propagate to Cost Explorer for chargeback.
```

## Skill output — custom IdP SFTP+FTPS on VPC endpoint

```text
SERVER: prod-sftp-vpc-custom-idp
VERDICT: READY_TO_DEPLOY
TARGET: prod-sftp-vpc-custom-idp
PRE_CHECKS:
  - [PASS] Protocols valid: SFTP, FTPS
  - [PASS] Endpoint type: VPC_ENDPOINT
  - [PASS] Identity provider: API_GATEWAY
  - [PASS] ACM cert abc-123 ISSUED in us-east-1, subject prod-sftp.example.com
  - [PASS] API Gateway abc123 deployed to stage prod
  - [PASS] Invocation role TransferIdPInvocationRole trusts transfer.amazonaws.com with apigateway:Invoke
  - [PASS] IdP Lambda returns expected JSON shape (Role, HomeDirectory, Policy)
  - [PASS] Security group sg-ssh inbound port 22, sg-ftps inbound port 990
  - [PASS] VPC vpc-abc123 and subnets subnet-aaa, subnet-bbb all resolve
  - [PASS] Logging role TransferLoggingRole resolves
STEPS:
  1. CONFIRM: About to create-server prod-sftp-vpc-custom-idp in account
     111111111111 region us-east-1. This will CREATE a new VPC endpoint
     server with SFTP+FTPS protocols and a custom API Gateway Lambda IdP.
     Proceed? (yes/no)
  2. aws transfer create-server --description prod-sftp-vpc-custom-idp
     --protocols SFTP FTPS --endpoint-type VPC_ENDPOINT
     --identity-provider-type API_GATEWAY
     --identity-provider-details Url=https://abc123.execute-api.us-east-1.amazonaws.com/prod/,InvocationRole=arn:aws:iam::111111111111:role/TransferIdPInvocationRole
     --certificate arn:aws:acm:us-east-1:111111111111:certificate/abc-123
     --vpc-id vpc-abc123 --subnet-ids subnet-aaa subnet-bbb
     --security-group-ids sg-ssh sg-ftps
     --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole
POST_VERIFY:
  - (pending execution)
  - describe-server returns State=ONLINE, EndpointType=VPC_ENDPOINT
  - DNS resolves for the VPC endpoint address
  - Sample auth via API Gateway returns 200 OK with expected JSON shape
PROTOCOLS: SFTP, FTPS
ENDPOINT: VPC_ENDPOINT
IDP: APIGateway
STORAGE: S3 (per-user via Lambda response)
SESSION_POLICY_SCOPE: per-user via Lambda Policy field
WORKFLOWS: 0 attached
NOTES:
  - Custom IdP Lambda MUST return Role, HomeDirectory, and ideally Policy
    fields. Missing fields cause silent auth failures.
  - FTPS cert subject must match the hostname clients connect to.
  - VPC_ENDPOINT serves all AZs via a single endpoint — preferred for
    multi-AZ resilience.
```

## Skill output — FTP on PUBLIC blocked

```text
SERVER: legacy-ftp-public
VERDICT: PREREQUISITES_MISSING
TARGET: legacy-ftp-public
PRE_CHECKS:
  - [PASS] S3 bucket legacy-ftp-inbox exists in us-east-1
  - [PASS] IAM role TransferUserS3Role resolves with trust policy
  - [PASS] Logging role TransferLoggingRole resolves
  - [FAIL] Protocols=[FTP] on EndpointType=PUBLIC. Plain FTP sends
    username, password, and file contents in cleartext on the wire.
    Transfer Family requires VPC or VPC_ENDPOINT for FTP for this
    reason. The skill blocks FTP-on-PUBLIC at the pre-check gate.
STEPS: (none — pre-checks failed; switch to FTPS or move endpoint to VPC)
POST_VERIFY: (none)
PROTOCOLS: FTP (blocked on PUBLIC)
ENDPOINT: PUBLIC (incompatible with FTP)
IDP: ServiceManaged
STORAGE: S3 (bucket: legacy-ftp-inbox)
SESSION_POLICY_SCOPE: n/a (deployment blocked)
WORKFLOWS: 0 attached
NOTES:
  - Root cause: FTP requested on PUBLIC endpoint. FTP is unencrypted —
    credentials and file contents leak at the TCP layer.
  - Remediation option A: switch protocols to FTPS (encrypted control
    + data channels). FTPS on PUBLIC is acceptable for partner B2B
    with TLS-mandated clients.
  - Remediation option B: keep FTP but move endpoint to VPC_ENDPOINT.
    VPC keeps the unencrypted traffic within your network boundary —
    clients connect via VPN, Direct Connect, or VPC peering.
  - Re-issue the create-server CLI with one of:
    --protocols FTPS --endpoint-type PUBLIC --certificate <acm-arn>
    OR
    --protocols FTP --endpoint-type VPC_ENDPOINT --vpc-id <vpc> ...
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant
   emits `create-server` directly. The skill runs 10+ deterministic
   pre-checks and confirms the S3 bucket exists, IAM role trusts
   `transfer.amazonaws.com` with a `SourceAccount` condition, ACM
   cert is ISSUED for FTPS, security groups open the protocol ports.

2. **FTP-on-PUBLIC block.** A generic assistant creates an FTP server
   on a public endpoint and walks away. The skill blocks it at the
   pre-check gate — cleartext credentials on the internet are the
   worst-case silent regression.

3. **Per-user session policy enforcement.** A generic assistant
   creates users with the IAM role only. The skill requires a session
   policy on every `create-user` so the user is scoped to their home
   prefix — without it the user inherits the full role scope (the
   entire bucket).

4. **IAM trust `SourceAccount` / `SourceArn` condition.** A generic
   assistant trusts `transfer.amazonaws.com` with no condition. The
   skill locks the trust to your account (or specific server ARN) to
   prevent confused-deputy attacks.

5. **Custom IdP Lambda response shape.** A generic assistant wires the
   API Gateway IdP and assumes it works. The skill POSTs a sample
   username/password to the API and validates the Lambda returns
   `{Role, HomeDirectory, optional Policy, optional PublicKeys}` —
   missing fields cause silent auth failures.

6. **ACM cert validation for FTPS.** A generic assistant accepts any
   cert ARN. The skill verifies the cert is in the same region and
   status `ISSUED` — a pending cert causes FTPS handshake failures
   with no diagnostic pointing back to ACM.

7. **VPC_ENDPOINT preferred over VPC for multi-AZ.** A generic
   assistant uses the older VPC type (ENI per subnet). The skill
   prefers VPC_ENDPOINT (single endpoint serving all AZs) for
   production resilience.

8. **CONFIRM gate.** A generic assistant auto-executes. The skill
   emits `CONFIRM:` and waits — `create-server` cannot be trivially
   reversed and interacts with IAM, networking, and storage resources.

## Slash-command invocation

```
/aws:deploy-transfer-family
```

Or via the orchestrator:

```
/aws:pipeline
You: "create an SFTP server for partner B2B file exchange"
```

The orchestrator emits
`[Phase: Deploy | Skills routed: transfer-family-deployer]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create a transfer family sftp server"
# [Phase: Deploy | Skills routed: transfer-family-deployer]
```

## Live-account follow-up (optional, requires AWS CLI)

After the server is created:

```bash
# Verify server is ONLINE with expected protocols
aws transfer describe-server --server-id s-abc123def456 \
  --profile default \
  --query 'Server.[State,Protocols,EndpointType,IdentityProviderType]'

# Verify users with SSH keys, roles, home directories
aws transfer list-users --server-id s-abc123def456 \
  --profile default \
  --query 'Users[].[UserName,HomeDirectory]'

# Verify session policy is set on a user (the security boundary)
aws transfer describe-user --server-id s-abc123def456 \
  --user-name alice \
  --profile default \
  --query 'User.Policy'

# Verify CloudWatch logs are being written for SFTP operations
aws logs describe-log-streams \
  --log-group-name /aws/transfer/prod-sftp-inbox \
  --profile default \
  --order-by LastEventTime --descending --limit 3
```
