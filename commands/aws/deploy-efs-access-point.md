---
description: Provision EFS Access Points with POSIX identity, root directory, directory permissions, file-system policy (access-point-only Deny), per-AZ mount targets, TLS via amazon-efs-utils, EFS CSI driver for EKS, Lambda mounts, and Intelligent-Tiering. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create efs access point"
  - "provision efs access point"
  - "efs access point setup"
  - "posix identity efs"
  - "efs root directory"
  - "efs file system policy"
  - "elasticfilesystem accesspointarn"
  - "efs iam enforcement"
  - "amazon-efs-utils"
  - "efs tls mount"
  - "efs encryption in transit"
  - "efs mount target"
  - "efs cross-az mount"
  - "efs csi driver"
  - "eks efs persistent volume"
  - "ecs efs volume"
  - "lambda efs mount"
  - "efs intelligent-tiering"
  - "efs lifecycle"
routes_to: efs-access-point-deployer
---

# /aws:deploy-efs-access-point

Activate the `efs-access-point-deployer` skill and provision EFS
Access Points and their dependent primitives with production-grade
defaults.

## What it does

The skill walks a 9-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Confirm file-system baseline (encryption, throughput mode, lifecycle)
2. Verify a mount target exists in every AZ where compute runs
3. Install / verify amazon-efs-utils (or EFS CSI driver on EKS)
4. Create the access point (root directory, POSIX user, directory permissions)
5. Attach file-system policy with IAM enforcement (Null:AccessPointArn Deny)
6. Mount via the access point with TLS (`tls` mount option)
7. (ECS/EKS) Wire the access point into task/pod via EFS CSI driver
8. (Lambda) Configure function with VPC + access-point ARN
9. Verify every configuration item against actual state

## When to use

- You need an application-specific EFS entry point with POSIX identity.
- You must enforce IAM-based access to EFS (with the DNS-name bypass closed).
- You are mounting EFS from ECS or EKS via the EFS CSI driver (one AP per pod).
- You are mounting EFS from a Lambda function (with subnets in every AZ).
- You want TLS encryption in transit via amazon-efs-utils.
- You want to generate CloudFormation / Terraform for any of the above.

## How to invoke

### Slash command

```
/aws:deploy-efs-access-point
```

Then provide: file-system ID, account ID, region, AP name, root
directory, POSIX identity, and directory permissions. Add any
optional integrations (ECS, EKS, Lambda) and TLS preference.

### Natural language

Any of these routes to the same skill:

- "create an EFS access point"
- "enforce access-point-only mounts on EFS"
- "mount EFS from EKS with the CSI driver"
- "configure Lambda to mount EFS"
- "enable TLS encryption in transit for EFS"

### CLI routing

```bash
node cli/bin/cli.js route "create efs access point"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or harden
an EFS access point. The output checklist feeds into verification
pipelines and audit skills (efs-mount-troubleshooter for diagnosing
mount failures).

## Example

```
You: /aws:deploy-efs-access-point

     Provision an EFS access point for fs-0abc123def in us-east-1,
     account 123456789012. AP name team-a-ap, POSIX uid 1000 gid
     1000, root /data/team-a with perms 0750. Attach the file-system
     policy that forces access-point-only mounts via the
     Null:AccessPointArn Deny, and mount with TLS.

Skill:
  ACCESS_POINT: team-a-ap
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] File-system baseline: fs-0abc123def, Encrypted=true, ThroughputMode=bursting
    [✓] Mount targets in every compute AZ: 3 AZs covered
    [✓] amazon-efs-utils installed on EC2 ASG
    [✓] Access point created: team-a-ap (root: /data/team-a, uid: 1000, gid: 1000, perms: 0750)
    [✓] File-system policy: Deny on Null:AccessPointArn + Allow through AP
    [✓] Mount via AP alias with TLS: mount -t efs -o tls,accesspoint=fsap-xxxx
    [OPTIONAL] (ECS/EKS) Integration: not requested
    [OPTIONAL] (Lambda) Function VPC + AP: not requested
    [✓] Intelligent-Tiering lifecycle: TransitionTo IA after 30 days
  VERIFICATION_COMMANDS:
    aws efs describe-access-points --file-system-id fs-0abc123def
    aws efs describe-file-system-policy --file-system-id fs-0abc123def
    ...
```

## References

- Skill definition: `skills/efs-access-point-deployer/SKILL.md`
- Policy templates: `skills/efs-access-point-deployer/references/file-system-policy-examples.md`
- Provisioning CLI commands: `skills/efs-access-point-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/efs-access-point-deployer/evals/evals.json`
