---
name: transfer-family-deployer
description: >-
  Provisions AWS Transfer Family servers with secure defaults — SFTP,
  FTPS, and FTP protocols, server endpoint types (public vs VPC vs
  VPC_ENDPOINT), identity providers (Service Managed, API Gateway
  Lambda custom IdP, AWS Directory Service), S3 storage backend with
  scoped-down IAM roles and session policies, EFS-backed users,
  CloudWatch logging, security groups for VPC endpoints, AS2
  app-level B2B messaging, managed workflows (copy, delete, tag),
  tags, and structured logging. Runs pre-checks (S3 bucket policy,
  IAM role session policy scope, ACM cert for FTPS, API Gateway
  invocation permissions for custom IdP, VPC subnet/security group
  reachability, Directory Service user population), emits
  create-server and create-user CLIs behind a CONFIRM gate, and
  verifies via describe-server. Emits READY_TO_DEPLOY |
  PREREQUISITES_MISSING. Use when creating SFTP/FTPS servers,
  configuring custom IdPs, or setting up managed workflows.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws transfer create-server, create-user, update-server,
  describe-server, create-access, create-workflow (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - Transfer Family
  - AWS Transfer
  - SFTP
  - FTPS
  - FTP
  - AS2
  - file transfer
  - service managed
  - custom IdP
  - API Gateway
  - Lambda IdP
  - Directory Service
  - Managed Microsoft AD
  - S3 backend
  - EFS backend
  - session policy
  - IAM role
  - VPC endpoint
  - security group
  - managed workflows
  - CloudWatch logging
  - structured logging
tags: [transfer-family, sftp, ftps, storage, file-transfer, deploy, vpc, as2]
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
    - transfer-family
    - sftp
    - ftps
    - storage
    - file-transfer
    - deploy
    - vpc
    - as2
  dependencies:
    - aws-orchestrator
  keywords:
    - Transfer Family
    - SFTP
    - FTPS
    - custom IdP
    - API Gateway
    - session policy
    - managed workflows
    - AS2
  when_to_use: >-
    Creating an AWS Transfer Family server (SFTP, FTPS, FTP, AS2),
    configuring an identity provider (Service Managed, API Gateway
    Lambda custom IdP, AWS Directory Service), scoping IAM roles for
    per-user S3 access, deploying a VPC-attached server with security
    groups, enabling structured CloudWatch logging, or setting up
    managed workflows for inbound/outbound file processing.
  activation_triggers:
    - "create Transfer Family server"
    - "provision SFTP server"
    - "deploy FTPS server"
    - "Transfer Family custom IdP"
    - "API Gateway Lambda identity"
    - "Directory Service SFTP"
    - "Managed Microsoft AD SFTP"
    - "session policy S3"
    - "scoped-down IAM role"
    - "VPC endpoint Transfer Family"
    - "security group SFTP"
    - "EFS-backed users"
    - "Transfer Family managed workflow"
    - "AS2 app-level messaging"
    - "Transfer Family structured logging"
    - "create-server transfer"
    - "create-user transfer"
    - "Transfer Family tags"
  invocation_schema: >-
    Input: either (a) a Transfer Family deployment intent (create,
    update) with target server name, protocols (SFTP/FTPS/FTP/AS2),
    endpoint type (public/VPC/VPC_ENDPOINT), identity provider config,
    storage backend (S3 bucket or EFS), IAM role and session policy,
    logging config, security groups, and tags; OR (b) a server-id for
    live-account update or validation. Output: deterministic
    SERVER/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block per operation,
    where VERDICT is one of READY_TO_DEPLOY, PREREQUISITES_MISSING.
---

# Transfer Family Deployer

## What this skill does

Provisions AWS Transfer Family servers with secure storage defaults —
scoped-down IAM roles with session policies that confine each user to
their `home` directory, Service Managed or custom API Gateway Lambda
identity providers, FTPS / SFTP preferred over plain FTP, VPC-attached
endpoints for private connectivity, CloudWatch structured logging, and
managed workflows for inbound file processing. Runs deterministic
pre-checks before any state-changing CLI (does the S3 bucket exist and
does its policy allow the role? does the IAM role trust
`transfer.amazonaws.com`? does the ACM cert cover the FTPS endpoint?
does the API Gateway invocation role exist for the custom IdP? does the
VPC security group allow inbound on the protocol port?), emits the exact
`create-server` and `create-user` CLIs behind a CONFIRM gate, and
verifies the server via `describe-server`. Every server plan surfaces
the plain-FTP block, the unscoped-IAM-role warning, the public-endpoint
caveat, and the managed-workflow trigger ordering.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + pre-check priority order + protocol matrix | Before any operation |
| **Mindset** | Why session policies matter; Transfer Family silent failures; protocol trade-offs | Understanding the deployment model |
| **Pre-flight** | Server metadata gate — S3 bucket, IAM trust, ACM cert, VPC SG, IdP | Before executing any CLI |
| **Process** | Per-operation planning: create server, add user, configure workflow | When choosing which operation |
| **Common patterns** | Service Managed SFTP / custom IdP SFTP / FTPS VPC / AS2 boilerplate | Boilerplate lookup |
| **STRICT output contract** | Required SERVER/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block | Formatting the response |
| **NEVER (top 5)** | Hard rules that prevent insecure patterns | Review before deploy |
| **Expert heuristic** | Choosing identity provider and endpoint type | IdP/endpoint strategy |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | Any pre-check failed (S3 bucket missing, IAM role not trusting `transfer.amazonaws.com`, ACM cert in wrong region or pending for FTPS, API Gateway invocation role missing for custom IdP, VPC security group missing or wrong port, Directory Service not reachable, FTP requested on public endpoint, AS2 profile missing partner cert) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence with full server config, wait for operator yes |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY_TO_DEPLOY):**

1. **Protocol validity** — at least one of SFTP, FTPS, FTP, AS2 set. For
   `FTP` only, endpoint MUST be VPC or VPC_ENDPOINT (never PUBLIC).
2. **Endpoint type** — PUBLIC (internet-facing, service-managed
   networking) or VPC/VPC_ENDPOINT (private, your networking).
3. **Identity provider** — `ServiceManaged`, `API_GATEWAY` (custom Lambda
   IdP), or `AWS_DIRECTORY_SERVICE`. For `API_GATEWAY`: invocation role
   exists, the API endpoint is reachable, and the Lambda returns the
   expected JSON shape.
4. **S3 backend** — bucket exists in the same region; bucket policy
   grants the IAM role `s3:ListBucket`, `s3:GetObject`, `s3:PutObject`
   on the user's home prefix.
5. **IAM execution role** — trust policy allows `transfer.amazonaws.com`
   with `sts:AssumeRole` and (recommended) a `SourceArn` / `SourceAccount`
   condition locking the role to this server.
6. **Session policy scope** — every `create-user` call includes a
   `Policy` (session policy) that scopes the user to their home prefix.
   Unscoped users can read/write the entire bucket.
7. **Logging** — `LoggingRole` ARN provided; role has
   `logs:CreateLogStream`, `logs:CreateLogGroup`, `logs:PutLogEvents`
   on the CloudWatch log group resource.
8. **FTPS ACM cert** — for FTPS protocol, ACM cert ARN in the same
   region, status `ISSUED`, cert subject matches the FTPS hostname.
9. **VPC endpoint config** — for VPC_ENDPOINT: VPC ID, subnet IDs, and
   security group IDs all exist; the security group inbound rule covers
   the protocol port (22/SFTP, 21/FTP, 990/FTPS, 5082/AS2).
10. **Directory Service** — for `AWS_DIRECTORY_SERVICE`: the directory
    ID resolves via `ds:describe-directories`; the directory is in the
    same VPC as the server; the Transfer service has been granted
    access.
11. **AS2 profiles** — for AS2: local profile (with private key in
    Secrets Manager) and partner profile (with partner cert) both
    exist.
12. **Managed workflow** — for workflows: every step's Lambda/function
    ARN resolves; the workflow execution role trusts
    `transfer.amazonaws.com` and the workflow is referenced via
    `OnPartialUpload` / `OnUpload`.
13. **IAM permissions** — the operator principal holds
    `transfer:CreateServer` and `iam:PassRole`.

**Transfer Family limits (2026):**

- Servers per account (default): 100 (soft limit, raisable).
- Users per server: 5000 (Service Managed); Directory Service: governed
  by the directory size.
- Concurrent files per server: governed by instance capacity (default
  sizing auto-scales).
- Tags per server: 50.
- AS2 messages per server: unlimited (subject to throughput limits).
- VPC endpoint servers per VPC: soft limit, raisable via Support.

## Mindset

**One-line takeaway:** the IAM role on a Transfer Family user is the
whole security boundary. A user with `s3:*` on the role and no session
policy can read and write the entire bucket — every other user's
files, system objects, bucket-level operations. The role defines
maximum scope; the session policy (`--policy` on `create-user`) defines
the user's effective scope. Three Transfer Family realities drive
this:

- **Session policies are scoped-down IAM at runtime.** The effective
  permissions are the intersection of the IAM role policy AND the
  session policy. If the IAM role has `s3:GetObject` on `*` but the
  session policy has `s3:GetObject` on `home/bob/*`, the user can only
  read `home/bob/*`. Without a session policy, the user inherits the
  full IAM role scope.

- **Custom IdP responses silently fail.** A custom IdP API Gateway /
  Lambda that returns malformed JSON (missing `Role`, `HomeDirectory`,
  or `Policy` fields) causes Transfer Family to reject the auth with a
  generic "authentication failed" — no diagnostic about which field
  was wrong. Pre-flight testing of the IdP response shape is
  non-negotiable.

- **Plain FTP is unencrypted on the wire.** Username, password, and
  file contents are sent in cleartext. Transfer Family enforces this
  by requiring VPC/VPC_ENDPOINT for plain FTP — but a misconfigured
  public endpoint with FTP enabled is the worst-case silent
  regression. The skill blocks FTP-on-PUBLIC at the pre-check gate.

## Pre-flight: server metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-servers` returns at most 1000 servers per page.
Use `--next-token` to drain.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws transfer list-servers` — confirm the server name does not
   collide (note: Transfer Family uses server-id, not names; tags hold
   the human-readable name).
2. `aws transfer describe-server --server-id <id>` — capture the full
   server config for snapshot/diff.
3. `aws s3api head-bucket --bucket <bucket>` — verify S3 backend exists
   in the same region.
4. `aws s3api get-bucket-policy --bucket <bucket>` — verify the bucket
   policy grants the IAM role.
5. `aws iam get-role --role-name <TransferUserRole>` — verify the
   execution role exists and trusts `transfer.amazonaws.com`.
6. `aws iam get-role-policy --role-name <role> --policy-name <policy>`
   or `aws iam list-attached-role-policies` — verify the role has S3
   permissions.
7. `aws acm describe-certificate --certificate-arn <arn>` — for FTPS,
   verify cert is ISSUED in the same region.
8. `aws ec2 describe-security-groups --group-ids <sg-ids>` — for VPC
   endpoints, verify the SGs exist and inbound rules match protocols.
9. `aws ds describe-directories --directory-ids <id>` — for
   AWS_DIRECTORY_SERVICE, verify the directory exists and is ACTIVE.
10. `aws apigateway get-rest-api --rest-api-id <id>` — for
    `API_GATEWAY` IdP, verify the API exists and the stage is deployed.
11. `aws lambda get-policy --function-name <idp-lambda>` — for custom
    IdP, verify the API Gateway principal can invoke the Lambda.
12. `aws transfer list-workflows` — for managed workflow reference,
    verify the workflow exists and is ACTIVE.

**Malformed input:** if the server spec is missing required fields
(`Protocols`, endpoint type, identity provider type, or storage
backend), emit `VERDICT: PREREQUISITES_MISSING` with `REASON: Server
spec missing required field — Protocols, EndpointType,
IdentityProviderType, or storage backend. Cannot plan.` and
`REMEDIATION: Provide the full server config per
https://docs.aws.amazon.com/transfer/latest/userguide/create-server-cli.html.`

| Attribute | Effect on operation |
|---|---|
| FTP on PUBLIC endpoint | Cleartext credentials on the internet. PREREQUISITES_MISSING — blocked. |
| IAM role without session policy on user | User can read entire bucket. Flag in NOTES; require session policy. |
| S3 bucket in different region | Latency and cross-region data transfer costs. PREREQUISITES_MISSING. |
| IAM role not trusting `transfer.amazonaws.com` | Server cannot assume role for the user. PREREQUISITES_MISSING. |
| ACM cert pending for FTPS | FTPS handshake fails at runtime. PREREQUISITES_MISSING. |
| VPC security group missing inbound on port 22 | SFTP connections time out silently. PREREQUISITES_MISSING. |
| Custom IdP API Gateway not deployed to stage | Auth calls return 403/404. PREREQUISITES_MISSING. |
| AS2 partner cert not uploaded | AS2 messages cannot be encrypted. PREREQUISITES_MISSING. |
| Directory Service not in same VPC as server | Auth requests time out. PREREQUISITES_MISSING. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Transfer Family behaviors

These behaviors are easy to misjudge without operational Transfer
Family experience. Each changes a plan if ignored:

- **Protocols gate the endpoint type.** Plain FTP REQUIRES a VPC or
  VPC_ENDPOINT (never PUBLIC). FTPS supports any endpoint type but
  PUBLIC FTPS still leaks metadata. SFTP over PUBLIC is acceptable but
  VPC is preferred for partner B2B. AS2 only supports VPC/VPC_ENDPOINT.

- **IAM role = max scope; session policy = effective scope.** The
  Transfer Family service assumes the IAM role on behalf of the user
  for every S3 operation. The session policy (passed via `--policy` on
  `create-user` or returned by the custom IdP) is intersected with the
  role's identity-based policies to produce the effective permission
  set. Always pass a session policy that scopes the user to their home
  directory.

- **HomeDirectoryType: LOGICAL vs PATH.** `PATH` is the literal S3
  prefix. `LOGICAL` lets you map virtual directories to different S3
  prefixes via `HomeDirectoryMappings` — useful for chroot-like
  isolation. Default is `PATH`; use `LOGICAL` only when you need
  multi-folder mappings.

- **Service Managed users use SSH keys, not passwords.** Each user
  is created with `--ssh-public-key-body` (an SSH public key in
  OpenSSH format). Passwords are not supported for Service Managed
  SFTP users — rotate keys, not passwords.

- **Custom IdP response shape is non-negotiable.** The Lambda behind
  the API Gateway must return JSON with at minimum: `Role` (IAM ARN),
  `HomeDirectory` (S3 prefix), and optionally `Policy` (session policy
  JSON string), `HomeDirectoryType`, `PublicKeys`. Missing fields cause
  silent auth failures.

- **Directory Service SFTP uses AD credentials.** Users sign in with
  their `DOMAIN\username` and AD password — no SSH keys. The Directory
  Service must be a Managed Microsoft AD in the same VPC. Simple AD is
  not supported.

- **FTPS requires an ACM cert in the server's region.** The cert's
  subject MUST match the FTPS hostname clients connect to. Wildcard
  certs work for subdomains. Self-signed certs are technically
  supported but rejected by most client SFTP libraries.

- **VPC endpoint servers create an ENI in your VPC.** Clients connect
  to the ENI's private IP. You control networking (security groups,
  route tables, DNS). VPC_ENDPOINT (newer) lets you attach the server
  to your VPC without provisioning an ENI per subnet — preferred for
  multi-AZ resilience.

- **Logging role writes structured logs to CloudWatch.** Each
  user-level operation (upload, download, list, mkdir) is logged with
  a structured JSON payload. Without a `LoggingRole`, no audit trail.

- **AS2 uses local and partner profiles.** AS2 (RFC 4130) is B2B
  app-level file exchange over HTTP. Each partner needs a local profile
  (private key in Secrets Manager) and a partner profile (partner's
  cert). MDN (Message Disposition Notification) is asynchronous by
  default.

- **Managed workflows fire on partial or complete upload.**
  `OnPartialUpload` fires when bytes are received (chunked transfers).
  `OnUpload` fires when the file is fully written. Each workflow step
  is a Lambda, EKS task, or service step (copy, delete, tag). Workflows
  run in order; a failure can retry, abort, or continue.

- **Tags propagate for cost allocation.** Tag the server, not users.
  Tags like `Environment=prod` and `Partner=acme` flow through to
  Cost Explorer for chargeback.

- **Server endpoint DNS resolves after creation.** For PUBLIC servers,
  the endpoint is `s-<id>.server.transfer.<region>.amazonaws.com`.
  For VPC servers, you control DNS — typically a Route 53 private
  hosted zone record pointing at the server's VPC endpoint.

- **Pre-signed URLs for file operations.** Transfer Family uses
  pre-signed S3 URLs internally for uploads/downloads — the IAM role
  must have `s3:GetObject` and `s3:PutObject` for the URL generation
  to succeed, even when the session policy scopes the path.

### Step 1: Pre-check gate — PREREQUISITES_MISSING if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is
PREREQUISITES_MISSING with the failed checks enumerated in PRE_CHECKS.
Do NOT execute.

**For ALL operations:**
1. At least one of SFTP, FTPS, FTP, AS2 in `Protocols`.
2. `EndpointType` is one of `PUBLIC`, `VPC`, `VPC_ENDPOINT`.
3. `IdentityProviderType` is `SERVICE_MANAGED`, `API_GATEWAY`, or
   `AWS_DIRECTORY_SERVICE`.
4. Storage backend is provided (S3 bucket name or EFS file system ID).
5. `LoggingRole` ARN provided and resolves via `iam:get-role`.
6. Logging role has CloudWatch Logs permissions on the log group.
7. The operator principal holds `transfer:CreateServer` and
   `iam:PassRole`.

**For FTP protocol:**
8. `EndpointType` is `VPC` or `VPC_ENDPOINT` (FTP on PUBLIC is BLOCKED).
9. VPC security group inbound rule on port 21.

**For SFTP protocol:**
10. If PUBLIC: NOTE that VPC is recommended for partner B2B.
11. If VPC/VPC_ENDPOINT: security group inbound rule on port 22.

**For FTPS protocol:**
12. `Certificate` ARN provided.
13. ACM cert is in the same region as the server.
14. `describe-certificate` returns status `ISSUED`.
15. Cert subject/alt names cover the FTPS hostname.
16. If VPC: security group inbound rule on port 990 (and 21 for
    implicit FTPS control channel).

**For AS2 protocol:**
17. `EndpointType` is `VPC` or `VPC_ENDPOINT`.
18. Local profile exists (`describe-profile`).
19. Partner profile exists with partner cert.
20. Security group inbound rule on port 5082.

**For S3 backend:**
21. Bucket exists in the same region.
22. Bucket policy or IAM role grants `s3:ListBucket`,
    `s3:GetObject`, `s3:PutObject` on the intended prefix.
23. Bucket versioning status known (recommend Suspended or Enabled for
    audit).
24. IAM execution role trusts `transfer.amazonaws.com`.
25. Recommended: trust policy has `aws:SourceAccount` or
    `aws:SourceArn` condition locking to this account/server.

**For EFS backend:**
26. EFS file system ID resolves.
27. EFS access point configured (optional but recommended).
28. IAM role has `elasticfilesystem:ClientMount`,
    `elasticfilesystem:ClientWrite`.

**For API_GATEWAY custom IdP:**
29. `InvocationRole` ARN resolves via `iam:get-role`.
30. Invocation role trusts `transfer.amazonaws.com` and has
    `apigateway:Invoke` on the REST API.
31. `Url` is HTTPS, REST API deployed to a stage.
32. Pre-flight test: POST a sample username/password to the API and
    verify the response shape (Role, HomeDirectory, optional Policy).

**For AWS_DIRECTORY_SERVICE:**
33. Directory ID resolves via `ds:describe-directories`.
34. Directory status is ACTIVE.
35. Directory is in the same region and VPC.

**For managed workflow reference:**
36. Workflow ID resolves via `transfer:list-workflows`.
37. Workflow status is ACTIVE.
38. Workflow steps' Lambda/function ARNs all resolve.
39. Workflow execution role trusts `transfer.amazonaws.com` and has
    `lambda:InvokeFunction` on each step's Lambda.

**For VPC/VPC_ENDPOINT:**
40. VPC ID, subnet IDs, security group IDs all resolve via
    `ec2:describe-*`.
41. Security group inbound rules match the protocol ports.
42. (VPC_ENDPOINT only) the endpoint service name resolves.

### Step 2: READY_TO_DEPLOY — emit deployment plan

If all pre-checks pass, emit `VERDICT: READY_TO_DEPLOY` with the exact
CLI sequence and the CONFIRM gate. The plan includes:

- The exact `aws transfer create-server` CLI with the full config
  (Protocols, EndpointType, IdentityProviderType, LoggingRole,
  Certificate for FTPS, VPC/subnet/SG for VPC, tags).
- The follow-up `create-user` CLIs for each Service Managed user with
  their SSH public key, IAM role, HomeDirectory, and session Policy.
- The follow-up `create-access` CLI for S3 bucket access mapping
  (when the user's IAM role is the access entry).
- The follow-up `create-workflow` CLI (if managed workflow configured).
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-server`, `update-server`, `delete-server`), emit:
  `CONFIRM: About to <operation> Transfer Family server <id-or-name>
  in account <account> region <region>. This will <consequence>.
  Proceed? (yes/no)`. Do NOT execute until the operator confirms.
- Snapshot the current server config before modification:
  `aws transfer describe-server --server-id <id> --output json >
  /tmp/server-<id>-backup-$(date +%s).json`.
- Execute the CLI with the full server config.

### Step 4: Post-verification

After the operation finishes, run post-verification:

1. `describe-server --server-id <id>` returns `State: ONLINE` and the
   expected config (Protocols, IdentityProviderType, EndpointType).
2. For PUBLIC servers: DNS resolution of
   `s-<id>.server.transfer.<region>.amazonaws.com` succeeds.
3. For VPC/VPC_ENDPOINT: the ENI or VPC endpoint is in the expected
   subnet.
4. For Service Managed users: `describe-user --server-id <id>
   --user-name <user>` returns the user with the SSH key, role, and
   home directory.
5. For custom IdP: trigger a sample auth via the API Gateway and
   confirm the Lambda returns the expected JSON shape.
6. For managed workflows: trigger a sample upload to the
   `OnUpload`-mapped directory and confirm the workflow executes.

## Common server patterns (boilerplate)

### Service Managed SFTP — S3 backend (public endpoint)

```bash
# Trust policy for the Transfer user execution role
cat > transfer-user-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "transfer.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {"StringEquals": {"aws:SourceAccount": "111111111111"}}
  }]
}
EOF

aws iam create-role \
  --role-name TransferUserS3Role \
  --assume-role-policy-document file://transfer-user-trust.json

# Inline policy: maximum scope (session policy narrows per-user)
aws iam put-role-policy \
  --role-name TransferUserS3Role \
  --policy-name S3Access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": "arn:aws:s3:::prod-sftp-inbox"},
      {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], "Resource": "arn:aws:s3:::prod-sftp-inbox/*"}
    ]
  }'

# Logging role
aws iam create-role --role-name TransferLoggingRole \
  --assume-role-policy-document file://transfer-user-trust.json
aws iam attach-role-policy --role-name TransferLoggingRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSTransferLoggingAccess

# Create the server (Service Managed SFTP, public endpoint)
aws transfer create-server \
  --description "prod-sftp-inbox" \
  --protocols SFTP \
  --endpoint-type PUBLIC \
  --identity-provider-type SERVICE_MANAGED \
  --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole \
  --tags Key=Environment,Value=prod Key=Name,Value=prod-sftp-inbox

# Returns: { "ServerId": "s-abc123def456" }

# Add a user with a session policy scoping them to home/alice/
aws transfer create-user \
  --server-id s-abc123def456 \
  --user-name alice \
  --role arn:aws:iam::111111111111:role/TransferUserS3Role \
  --home-directory "/prod-sftp-inbox/alice" \
  --home-directory-type PATH \
  --ssh-public-key-body "ssh-rsa AAAAB3...alice@laptop" \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": "arn:aws:s3:::prod-sftp-inbox", "Condition": {"StringLike": {"s3:prefix": ["alice/*","alice"]}}},
      {"Effect": "Allow", "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject"], "Resource": "arn:aws:s3:::prod-sftp-inbox/alice/*"}
    ]
  }'
```

### Custom IdP via API Gateway + Lambda (VPC endpoint)

```bash
# Invocation role for Transfer Family to call the API Gateway
aws iam create-role \
  --role-name TransferIdPInvocationRole \
  --assume-role-policy-document file://transfer-user-trust.json
aws iam put-role-policy \
  --role-name TransferIdPInvocationRole \
  --policy-name InvokeIdP \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "apigateway:Invoke",
      "Resource": "arn:aws:apigateway:us-east-1::/restapis/abc123/stages/prod/POST/"
    }]
  }'

aws transfer create-server \
  --description "prod-sftp-vpc-custom-idp" \
  --protocols SFTP FTPS \
  --endpoint-type VPC \
  --identity-provider-type API_GATEWAY \
  --identity-provider-details '{
    "Url": "https://abc123.execute-api.us-east-1.amazonaws.com/prod/",
    "InvocationRole": "arn:aws:iam::111111111111:role/TransferIdPInvocationRole"
  }' \
  --certificate arn:aws:acm:us-east-1:111111111111:certificate/abc-123 \
  --address-allocation-id allocation-id-elastic-ip \
  --vpc-id vpc-abc123 \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-ssh sg-ftps \
  --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole \
  --tags Key=Environment,Value=prod
```

### Directory Service (Managed AD), FTPS, AS2 — short forms

Directory Service SFTP uses `--identity-provider-type AWS_DIRECTORY_SERVICE --identity-provider-details '{"DirectoryId":"d-abc123"}'` with `--endpoint-type VPC_ENDPOINT`. FTPS requires `--certificate <acm-arn>` in the same region. AS2 uses `--protocols AS2 --endpoint-type VPC_ENDPOINT` followed by `create-profile` for local and partner profiles. Full CLI sequences in `references/identity-providers-and-storage.md`.

### Managed workflow (OnUpload — process inbound file)

```bash
# Execution role trusts transfer.amazonaws.com with lambda:InvokeFunction on the step Lambda
aws transfer create-workflow \
  --description "Process inbound SFTP file" \
  --steps '[{"Type":"COPY","CopyStepDetails":{"DestinationFileLocation":{"S3FileLocation":{"Bucket":"prod-processed","Key":"inbound"}},"SourceFileLocation":"${originalFile}"}},{"Type":"CUSTOM","CustomStepDetails":{"Target":"arn:aws:lambda:us-east-1:111111111111:function:process-inbound-file"}}]' \
  --on-exception-steps '[{"Type":"DELETE","DeleteStepDetails":{"SourceFileLocation":"${originalFile}"}}]'

# Reference the workflow on the server via update-server --workflow-details '{"OnUpload":{"WorkflowId":"w-abc123","ExecutionRole":"arn:aws:iam::111111111111:role/TransferWorkflowExecutionRole"}}'
```

Full managed-workflow CLI sequence with execution role setup is in `references/identity-providers-and-storage.md`.

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
SERVER: <description-or-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <description-or-name> (server-id: <id> for updates)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> server <name> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
PROTOCOLS: SFTP | FTPS | FTP | AS2 (combinations)
ENDPOINT: PUBLIC | VPC | VPC_ENDPOINT
IDP: ServiceManaged | APIGateway | DirectoryService
STORAGE: S3 (bucket: <name>) | EFS (fs: <id>)
SESSION_POLICY_SCOPE: <home-prefix-per-user> | (none — UNSCOPED, blocked)
WORKFLOWS: <count> attached
NOTES: <security posture, IAM scope, protocol caveats>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll create…" — the VERDICT
  block is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING` (not `ready`, `prerequisites`).
- NEVER omit PRE_CHECKS — every pre-check run must appear with `[PASS]`
  or `[FAIL]` and a specific reason for each failure. An empty
  PRE_CHECKS block is non-compliant.
- NEVER emit a plan with placeholder values (e.g., `<server-id>`,
  `<account-id>`) in a READY_TO_DEPLOY plan — every field must be
  populated with actual values from the input.
- NEVER omit the CONFIRM gate as the first STEPS entry for any
  state-changing operation.
- NEVER claim success without verifying the server is ONLINE (via
  `describe-server`).
- NEVER silently allow FTP on PUBLIC endpoint — block it explicitly
  with a [FAIL] pre-check row naming the cleartext credential risk.
- NEVER create a user without a session policy — unscoped users can
  read the entire bucket. If the input omits it, the skill inserts a
  default scoped to the home prefix and flags in NOTES.

### Perfect example output

```text
SERVER: prod-sftp-inbox
VERDICT: READY_TO_DEPLOY
TARGET: prod-sftp-inbox
PRE_CHECKS:
  - [PASS] Protocols valid: SFTP
  - [PASS] Endpoint type: PUBLIC (acceptable for SFTP; VPC preferred for partner B2B)
  - [PASS] Identity provider: SERVICE_MANAGED
  - [PASS] S3 bucket prod-sftp-inbox exists in us-east-1
  - [PASS] IAM role TransferUserS3Role trusts transfer.amazonaws.com with SourceAccount condition
  - [PASS] IAM role has s3:ListBucket, s3:GetObject, s3:PutObject on bucket
  - [PASS] Logging role TransferLoggingRole resolves with logs:* permissions
  - [PASS] Operator principal holds transfer:CreateServer and iam:PassRole
STEPS:
  1. CONFIRM: About to create-server prod-sftp-inbox in account 111111111111 region us-east-1. This will CREATE a new Transfer Family server with SFTP protocol, Service Managed IdP, and CloudWatch logging. Proceed? (yes/no)
  2. aws transfer create-server --description prod-sftp-inbox --protocols SFTP --endpoint-type PUBLIC --identity-provider-type SERVICE_MANAGED --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole --tags Key=Environment,Value=prod
  3. aws transfer create-user --server-id <returned-id> --user-name alice --role arn:aws:iam::111111111111:role/TransferUserS3Role --home-directory /prod-sftp-inbox/alice --ssh-public-key-body "ssh-rsa AAAAB3..." --policy '{session policy scoping to /alice/*}'
POST_VERIFY:
  - (pending execution)
  - describe-server returns State=ONLINE
  - describe-user returns alice with SSH key, role, home directory, and session policy
PROTOCOLS: SFTP
ENDPOINT: PUBLIC
IDP: ServiceManaged
STORAGE: S3 (bucket: prod-sftp-inbox)
SESSION_POLICY_SCOPE: per-user home prefix
WORKFLOWS: 0 attached
NOTES:
  - PUBLIC endpoint exposes SFTP to the internet — VPC endpoint preferred for partner B2B.
  - Session policy scopes alice to /prod-sftp-inbox/alice/* — without it she could read the whole bucket.
  - Tags Environment=prod propagate to Cost Explorer for chargeback.
```

## NEVER (top 5)

These are the highest-impact, most-frequent failure modes in Transfer
Family deployments. Violating any one is a security or availability
regression.

1. **NEVER enable FTP on a PUBLIC endpoint.** Plain FTP sends
   username, password, and file contents in cleartext on the wire.
   Transfer Family requires VPC/VPC_ENDPOINT for FTP for this reason.
   A misconfigured public FTP server leaks credentials at the TCP
   layer — block at pre-check.

2. **NEVER create a user without a session policy.** The IAM role
   defines the user's MAX scope. Without a session policy, the user
   inherits the full role scope — typically every user's files, every
   prefix, and potentially bucket-level operations. Always pass
   `--policy` scoping the user to their home prefix. The skill inserts
   a default if the input omits it.

3. **NEVER use an IAM execution role that trusts
   `transfer.amazonaws.com` without a `SourceAccount` / `SourceArn`
   condition.** A bare trust policy lets any AWS account's Transfer
   Family server assume the role via confused-deputy. Lock the trust
   to your account (or specific server ARN) via the condition.

4. **NEVER deploy FTPS without verifying the ACM cert status is
   ISSUED.** A pending or rejected cert causes the FTPS handshake to
   fail at runtime — clients see generic TLS errors with no diagnostic
   pointing back to ACM. Verify in the same region as the server and
   confirm the subject matches the hostname clients connect to.

5. **NEVER configure a custom IdP API Gateway without pre-flight
   testing the Lambda response shape.** A missing `Role`,
   `HomeDirectory`, or `Policy` field causes auth to fail with a
   generic "authentication failed" error — no diagnostic about which
   field was wrong. POST a sample username/password to the API and
   validate the JSON shape before declaring the server ready.

## Expert heuristic: choosing identity provider and endpoint type

The right IdP and endpoint type is a function of user population,
credential source, and network exposure — not a one-size-fits-all.

```
Identity provider
   ├─ Consumer / one-off partners (small user count)?
   │    └─ SERVICE_MANAGED. SSH keys per user. No password to leak,
   │         no IdP infrastructure to operate. Best UX if you can
   │         distribute SSH keys.
   │
   ├─ Workforce users in Active Directory?
   │    └─ AWS_DIRECTORY_SERVICE. Users sign in with DOMAIN\user +
   │         AD password — no SSH keys. Requires Managed Microsoft AD
   │         in the same VPC. Simple AD is NOT supported.
   │
   ├─ External partners with their own IdP (Okta, Auth0, custom)?
   │    └─ API_GATEWAY custom Lambda IdP. Your Lambda receives
   │         username/password (or SSH key fingerprint) and returns
   │         {Role, HomeDirectory, Policy, PublicKeys}. Maximum
   │         flexibility — centralizes user mapping, MFA, audit.
   │
   └─ AS2 partners (B2B app-level)?
        └─ Local + partner profile cert exchange. AS2 uses mutual
             cert-based auth — not username/password.

Endpoint type
   ├─ Internet-facing SFTP for ad-hoc partner onboarding?
   │    └─ PUBLIC. Acceptable for SFTP. Use security groups and IP
   │         allow-lists where possible. FTPS on PUBLIC exposes TLS
   │         metadata.
   │
   ├─ Private partner B2B (regulated, internal-only)?
   │    └─ VPC_ENDPOINT. Your VPC, your SGs, your Route 53. Partner
   │         connects via VPN/Direct Connect/peering.
   │
   ├─ Multi-AZ resilience for production SFTP?
   │    └─ VPC with subnets in 2+ AZs. VPC_ENDPOINT preferred —
   │         single endpoint serves all AZs without per-subnet ENI.
   │
   └─ AS2 or FTP (required private)?
        └─ VPC_ENDPOINT only. FTP never on PUBLIC (blocked).
```

**Decision rules:**
- Default to SERVICE_MANAGED + SSH keys. Switch to custom IdP only when
  you need password auth, MFA, or central user management.
- Default to VPC_ENDPOINT for production. PUBLIC is acceptable for
  SFTP pilots but exposes metadata.
- Always pass a session policy scoping the user to their home prefix.
- Always pair `LoggingRole` with the structured-logging managed policy
  — without logs you have no audit trail of who uploaded what.
- FTPS requires ACM cert in the same region; SFTP does not.
- AS2 is a separate operational model — local/partner profile cert
  exchange, MDN acks, no SSH key distribution.

ALWAYS tag the server with `Environment` and (for partner servers)
`Partner` — these tags propagate to Cost Explorer for chargeback.

## Recent AWS features (2024-2026)

- **Transfer Family AS2 (2023-2024 GA):** app-level B2B file exchange
  over HTTP/HTTPS, RFC 4130 compliant. Local and partner profiles with
  cert-based mutual auth. Asynchronous MDN by default. Replaces the
  need for a third-party AS2 gateway for many B2B integrations.
- **Managed workflows (2024-2025):** native step-based workflow engine
  triggered `OnUpload` or `OnPartialUpload`. Step types: COPY, DELETE,
  TAG, CUSTOM (Lambda). Exception steps run on failure. Replaces the
  common pattern of EventBridge + Lambda for inbound file processing.
- **VPC_ENDPOINT endpoint type (2024-2025):** attaches the server to
  your VPC without provisioning a per-subnet ENI. Single endpoint
  serves all AZs. Preferred over the older VPC type for multi-AZ
  resilience.
- **Structured CloudWatch logging (2024):** JSON-formatted logs with
  user, file, operation, and timestamp fields. Replaces the older
  text-format logs. Queryable via CloudWatch Logs Insights.
- **EFS storage backend (2024-2025):** EFS-backed home directories for
  users requiring POSIX file system semantics. Optional EFS access
  points for chroot-like isolation. S3 remains the most common
  backend.
- **Directory Service Simple AD deprecation (2025):** Simple AD no
  longer supported for new Transfer Family servers. Use Managed
  Microsoft AD only.
- **Tag-based access control (2024-2025):** ABAC via resource tags
  on the server and user — useful for multi-tenant Transfer Family
  deployments.
- **Per-server throttling and queueing (2024-2025):** server-side
  queueing of concurrent connections beyond the per-server limit,
  removing silent connection drops under load.

## AWS documentation

- **AWS Transfer Family User Guide** — https://docs.aws.amazon.com/transfer/latest/userguide/what-is-aws-transfer.html
- **Create server (CLI)** — https://docs.aws.amazon.com/transfer/latest/userguide/create-server-cli.html
- **Service Managed users** — https://docs.aws.amazon.com/transfer/latest/userguide/configure-sftp-users.html
- **Custom IdP (API Gateway + Lambda)** — https://docs.aws.amazon.com/transfer/latest/userguide/configuring-custom-idp.html
- **Directory Service SFTP** — https://docs.aws.amazon.com/transfer/latest/userguide/directory-service-users.html
- **SFTP session policies** — https://docs.aws.amazon.com/transfer/latest/userguide/session-policy.html
- **FTPS cert configuration** — https://docs.aws.amazon.com/transfer/latest/userguide/protocols.html
- **AS2 profiles** — https://docs.aws.amazon.com/transfer/latest/userguide/as2-profiles.html
- **Managed workflows** — https://docs.aws.amazon.com/transfer/latest/userguide/working-with-workflows.html
- **Structured logging** — https://docs.aws.amazon.com/transfer/latest/userguide/monitoring.html

## Domain

AWS CloudOps / Storage — Transfer Family Server Provisioning & File
Exchange.
