---
description: Provision an AWS Transfer Family server and managed workflows with production-grade defaults (SFTP/FTPS/FTP, identity provider selection, VPC_ENDPOINT for private SFTP, per-user session policy for S3 scoping, AS2 connectors for B2B exchange, managed workflows with Step Functions for file processing). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create transfer family"
  - "create sftp server"
  - "transfer family server"
  - "sftp server aws"
  - "transfer family lambda identity"
  - "transfer family vpc endpoint"
  - "sftp vpc endpoint"
  - "transfer family managed workflow"
  - "transfer family as2 connector"
  - "sftp session policy"
  - "transfer family home directory"
  - "managed file transfer"
  - "ftps server aws"
  - "as2 connector"
routes_to: transfer-family-workflow-deployer
---

# /aws:deploy-transfer-family-workflow

Activate the `transfer-family-workflow-deployer` skill and provision an
AWS Transfer Family server with managed workflows and production-grade
defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Server model and protocols (SFTP, FTPS, FTP)
2. Identity provider (service-managed, Directory Service, custom Lambda)
3. Endpoint type (PUBLIC, VPC, VPC_ENDPOINT)
4. VPC, subnets, security groups for private endpoints
5. Route 53 hosted zone DNS for custom hostnames
6. User home directory mapping (physical vs logical)
7. IAM role and session policy for per-user S3 scoping
8. Server host key and trusted host keys
9. AS2 connectors for B2B trading partner exchange
10. Managed workflows with Step Functions for file processing
11. Structured JSON logging to CloudWatch
12. Throttling and limits
13. Recent features (managed workflows, AS2, structured logging)

## When to use

- You need to create a Transfer Family SFTP/FTPS/FTP server.
- You are configuring a custom Lambda identity provider.
- You need a VPC endpoint for private SFTP access.
- You want to deploy managed workflows for file processing automation.
- You are setting up AS2 connectors for B2B EDI exchange.
- You need per-user session policies for S3 access scoping.

## When NOT to use

- **AWS DataSync** — use datasync skills for data migration tasks.
- **S3 direct access** — Transfer Family is for SFTP/FTPS/FTP protocol bridging.
- **Storage Gateway** — different service for on-premises storage integration.
- **Existing transfer-family deploy command** — this skill focuses on the
  full workflow lifecycle including managed workflows and AS2.

## How to invoke

### Slash command

```
/aws:deploy-transfer-family-workflow
```

Then provide: protocol (SFTP/FTPS/FTP), endpoint type, identity provider
type, VPC/subnet/security group IDs (for VPC/VPC_ENDPOINT), S3 bucket,
IAM role, session policy requirements, managed workflow configuration,
AS2 connector details (if applicable), tags.

### Natural language

Any of these routes to the same skill:

- "create an sftp server with custom lambda authentication"
- "set up a private sftp endpoint in my vpc"
- "deploy managed workflows for file processing"
- "configure an as2 connector for my trading partner"
- "create a transfer family server with session policies"

### CLI routing

```bash
node cli/bin/cli.js route "create transfer family sftp server"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or update
Transfer Family servers and workflows. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-transfer-family-workflow

     Create a Transfer Family SFTP server with VPC_ENDPOINT in
     vpc-aaa11122. Custom Lambda identity provider. Per-user
     session policy scoped to /file-landing-zone/home/<user>/*.
     Managed workflow: COPY to data lake, TAG, virus scan.

Skill:
  TRANSFER_FAMILY: s-abc123 (SFTP) — VPC_ENDPOINT
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Endpoint type: VPC_ENDPOINT (PrivateLink)
    [✓] Identity provider: Custom Lambda (transfer-idp-auth)
    [✓] Session policy: attached per-user (S3 scoped)
    [✓] Managed workflow: w-def456 (COPY → TAG → virus scan)
  VERIFICATION_COMMANDS:
    aws transfer describe-server --server-id s-abc123
    aws transfer describe-workflow --workflow-id w-def456
```

## References

- Skill definition: `skills/transfer-family-workflow-deployer/SKILL.md`
- Identity providers and endpoints: `skills/transfer-family-workflow-deployer/references/identity-providers-and-endpoints.md`
- Managed workflows and AS2: `skills/transfer-family-workflow-deployer/references/managed-workflows-and-as2.md`
- Eval suite: `skills/transfer-family-workflow-deployer/evals/evals.json`
