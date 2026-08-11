---
description: Provision an AWS Cloud9 environment with production-grade defaults (SSM no-ingress connection, Amazon Linux/Ubuntu platform, auto-hibernation, IAM instance profile, team sharing, CodeCommit/GitHub integration, EC2 lifecycle management, cost optimization). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create cloud9 environment"
  - "deploy cloud9 environment"
  - "cloud9 ssm connection"
  - "cloud9 no ingress"
  - "cloud9 auto hibernate"
  - "cloud9 sharing"
  - "cloud9 team sharing"
  - "cloud9 ec2 lifecycle"
  - "cloud9 cost optimization"
  - "cloud9 ubuntu"
  - "cloud9 amazon linux"
  - "cloud9 environment"
  - "cloud9 ide"
routes_to: cloud9-environment-deployer
---

# /aws:deploy-cloud9-environment

Activate the `cloud9-environment-deployer` skill and provision an AWS
Cloud9 environment with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Environment model (EC2-backed cloud IDE)
2. Connection mode (SSM no-ingress vs SSH with key pair)
3. Platform selection (Amazon Linux 2, Ubuntu)
4. Instance type and lifecycle (start/stop/delete)
5. Subnet and security group (no-ingress for SSM, port 22 for SSH)
6. IAM instance profile (AmazonSSMManagedInstanceCore for SSM)
7. Automatic hibernation (idle timeout for cost optimization)
8. Environment sharing (read-write, read-only memberships)
9. Git integration (CodeCommit, GitHub)
10. Recent features (SSM maturity, Ubuntu 22.04, CloudWatch, Terraform)

## When to use

- You need to create a Cloud9 environment.
- You want SSM-based no-ingress connection (recommended).
- You need auto-hibernation for cost optimization.
- You want to share a Cloud9 environment with team members.
- You need to manage Cloud9 EC2 lifecycle.
- You want to integrate Cloud9 with CodeCommit or GitHub.

## When NOT to use

- **AWS CloudShell** — browser-based shell, no provisioning needed.
- **AWS CodeBuild** — CI/CD build service, not an IDE.
- **AWS CodeStar** — project management, not IDE provisioning.
- **Auditing existing Cloud9 environments** — use Cloud9 audit skills.

## How to invoke

### Slash command

```
/aws:deploy-cloud9-environment
```

Then provide: environment name, instance type, platform (Amazon Linux/
Ubuntu), connection mode (SSM/SSH), subnet ID, instance profile name,
key pair name (if SSH), auto-hibernation minutes, sharing members,
Git integration, tags.

### Natural language

Any of these routes to the same skill:

- "create a Cloud9 environment with SSM connection"
- "set up a Cloud9 IDE with auto-hibernation"
- "share my Cloud9 environment with the dev team"
- "create a no-ingress Cloud9 on Ubuntu"
- "provision a cost-optimized Cloud9 for budget development"

### CLI routing

```bash
node cli/bin/cli.js route "create a cloud9 environment"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Cloud9
environments. The output checklist feeds into verification pipelines
and downstream audit skills.

## Example

```
You: /aws:deploy-cloud9-environment

     Create a Cloud9 environment named dev-team-ide. t3.medium,
     Amazon Linux 2, SSM connection mode. Subnet subnet-aaa11122.
     Instance profile Cloud9InstanceProfile. Auto-hibernate 30
     minutes. Share with teammate1 and teammate2 read-write.

Skill:
  CLOUD9_ENVIRONMENT: dev-team-ide
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Connection mode: SSM (CONNECT_SSM, no ingress)
    [✓] Instance profile: Cloud9InstanceProfile (includes AmazonSSMManagedInstanceCore)
    [✓] Auto-hibernation: 30 minutes
    [✓] Sharing: 2 members (2 read-write)
  VERIFICATION_COMMANDS:
    aws cloud9 describe-environments --environment-ids <env-id> --region us-east-1
```

## References

- Skill definition: `skills/cloud9-environment-deployer/SKILL.md`
- Connection modes and IAM guide: `skills/cloud9-environment-deployer/references/connection-modes-and-iam.md`
- Sharing and cost optimization guide: `skills/cloud9-environment-deployer/references/sharing-and-cost-optimization.md`
- Eval suite: `skills/cloud9-environment-deployer/evals/evals.json`
