---
description: Provision a production-grade AWS Transfer Family server with secure defaults — SFTP/FTPS/FTP/AS2 protocols, Service Managed / API Gateway Lambda / Directory Service identity providers, S3 or EFS backend with per-user session policy scoping, CloudWatch structured logging, VPC endpoint networking, managed workflows, and tags. Emits a READY_TO_DEPLOY checklist with verification commands and blocks FTP-on-PUBLIC plus unscoped IAM roles.
nl_triggers:
  - "create transfer family server"
  - "provision SFTP server"
  - "deploy FTPS server"
  - "AWS Transfer Family custom IdP"
  - "API Gateway Lambda identity provider"
  - "Directory Service SFTP"
  - "Managed Microsoft AD SFTP"
  - "Transfer Family session policy"
  - "scoped-down IAM role SFTP"
  - "VPC endpoint transfer family"
  - "security group SFTP"
  - "EFS-backed SFTP users"
  - "Transfer Family managed workflow"
  - "AS2 app-level messaging"
  - "Transfer Family structured logging"
  - "transfer create-server"
  - "transfer create-user"
  - "Transfer Family tags"
routes_to: transfer-family-deployer
---

# /aws:deploy-transfer-family

Activate the `transfer-family-deployer` skill and provision a
production-grade AWS Transfer Family server with secure storage and
identity defaults.

## What it does

The skill walks a pre-check gate and emits a READY_TO_DEPLOY checklist:

1. Protocols valid (SFTP, FTPS, FTP, AS2 — at least one set)
2. Endpoint type (PUBLIC, VPC, VPC_ENDPOINT) compatible with protocols
3. Identity provider (SERVICE_MANAGED, API_GATEWAY, AWS_DIRECTORY_SERVICE)
4. S3 backend (bucket exists in-region, IAM role trust + S3 permissions)
5. EFS backend (file system exists, IAM role has EFS permissions)
6. Per-user session policy (scopes each user to their home prefix)
7. IAM execution role trust (`transfer.amazonaws.com` with SourceAccount
   / SourceArn condition to prevent confused-deputy)
8. Logging role (CloudWatch Logs permissions for audit trail)
9. FTPS ACM cert (same region, status ISSUED, subject matches hostname)
10. VPC endpoint config (subnets, security groups with protocol ports)
11. API Gateway custom IdP (REST API deployed to stage, invocation role
    with apigateway:Invoke, Lambda returns expected JSON shape)
12. Directory Service (Managed Microsoft AD ACTIVE in matching VPC)
13. AS2 profiles (local profile with private key, partner profile with
    partner cert)
14. Managed workflows (workflow ID ACTIVE, execution role trusts
    transfer.amazonaws.com, OnUpload / OnPartialUpload trigger mapped)
15. Tags (Environment, Partner — propagate to Cost Explorer)

## When to use

- You need to create a new SFTP/FTPS/FTP/AS2 server with production defaults.
- You are configuring a custom API Gateway Lambda identity provider.
- You need Directory Service (Managed Microsoft AD) integration.
- You want per-user session policy scoping for S3 multi-tenant isolation.
- You need a VPC-attached server with security groups for private partner B2B.
- You want managed workflows for inbound file processing (COPY, TAG, CUSTOM).
- You need AS2 profiles for B2B app-level file exchange.
- You want structured CloudWatch logging for audit and compliance.

## How to invoke

### Slash command

```
/aws:deploy-transfer-family
```

Then provide: server description, region, protocols, endpoint type,
identity provider config (Service Managed / API Gateway / Directory
Service), storage backend (S3 bucket or EFS file system), IAM role and
per-user session policy, logging role, VPC config (VPC/subnets/SGs for
VPC endpoints), ACM cert (for FTPS), workflows, and tags.

### Natural language

Any of these routes to the same skill:

- "create an SFTP server for partner B2B file exchange"
- "deploy FTPS with a custom IdP via API Gateway"
- "configure Directory Service SFTP for workforce"
- "scope my SFTP users to their home directories"
- "set up a Transfer Family managed workflow on upload"
- "configure AS2 for B2B partner exchange"

### CLI routing

```bash
node cli/bin/cli.js route "create a transfer family sftp server"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or extend
Transfer Family servers. The output checklist feeds into verification
pipelines and audit skills for post-deploy security auditing.

## Example

```
You: /aws:deploy-transfer-family

     Create a Service Managed SFTP server "prod-sftp-inbox" in
     us-east-1 with S3 backend prod-sftp-inbox. Users alice and bob
     scoped to their home prefixes via session policy. Account:
     111111111111.

Skill:
  SERVER: prod-sftp-inbox
  VERDICT: READY_TO_DEPLOY
  TARGET: prod-sftp-inbox
  PRE_CHECKS:
    [PASS] Protocols valid: SFTP
    [PASS] Endpoint type: PUBLIC (acceptable for SFTP; VPC preferred for partner B2B)
    [PASS] S3 bucket prod-sftp-inbox exists in us-east-1
    [PASS] IAM role TransferUserS3Role trusts transfer.amazonaws.com with SourceAccount
    [PASS] Logging role TransferLoggingRole resolves with logs:* permissions
    [PASS] Operator principal holds transfer:CreateServer and iam:PassRole
  PROTOCOLS: SFTP
  ENDPOINT: PUBLIC
  IDP: ServiceManaged
  STORAGE: S3 (bucket: prod-sftp-inbox)
  SESSION_POLICY_SCOPE: per-user home prefix
```

## References

- Skill definition: `skills/transfer-family-deployer/SKILL.md`
- Server & IAM session policies: `skills/transfer-family-deployer/references/server-and-iam-session-policies.md`
- Identity providers, storage, workflows: `skills/transfer-family-deployer/references/identity-providers-and-storage.md`
- Eval suite: `skills/transfer-family-deployer/evals/evals.json`
