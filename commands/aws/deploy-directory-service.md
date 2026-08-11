---
description: Provision an AWS Directory Service directory with production-grade defaults (Managed Microsoft AD, Simple AD, or AD Connector; edition sizing; VPC/subnet placement; DNS conditional forwarders; trust relationships; LDAPS; SSO via IAM Identity Center; cross-account sharing; Multi-Region replication; password policies). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create managed microsoft ad"
  - "deploy managed ad"
  - "create simple ad"
  - "deploy simple ad"
  - "configure ad connector"
  - "directory service trust"
  - "enable ldaps"
  - "secure ldap"
  - "sso iam identity center"
  - "directory sharing"
  - "share directory"
  - "multi-region replication"
  - "directory password policy"
  - "directory service"
routes_to: directory-service-deployer
---

# /aws:deploy-directory-service

Activate the `directory-service-deployer` skill and provision an AWS
Directory Service directory with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Directory type selection (Managed AD vs Simple AD vs AD Connector)
2. Edition and sizing (Standard vs Enterprise; Small vs Large)
3. VPC and subnet placement (multi-AZ, private subnets)
4. DNS configuration (conditional forwarders on both sides)
5. Trust relationships (forest vs external, one-way vs two-way)
6. LDAPS (secure LDAP with certificate authority lifecycle)
7. SSO via IAM Identity Center
8. Cross-account directory sharing (handshake flow)
9. Multi-Region replication (Enterprise edition, manual failover)
10. Password policies and security group association
11. Snapshot and restore
12. Recent features

## When to use

- You need to create a Managed Microsoft AD directory.
- You are deploying Simple AD for basic LDAP needs.
- You are configuring AD Connector to proxy to on-prem AD.
- You need to set up a trust relationship (forest or external).
- You need to enable LDAPS (secure LDAP).
- You need to integrate with IAM Identity Center for SSO.
- You need to share a directory across accounts.
- You need Multi-Region replication for disaster recovery.
- You need to configure password policies.

## When NOT to use

- **Self-managed AD on EC2** — this skill covers managed Directory
  Service only, not self-managed AD instances.
- **Third-party LDAP servers** — use the relevant product-specific
  skills.
- **AWS Managed Microsoft AD audit/review** — use Directory Service
  audit skills.

## How to invoke

### Slash command

```
/aws:deploy-directory-service
```

Then provide: directory type, edition, VPC ID, subnet IDs (2 AZs),
DNS name, NetBIOS name, trust requirements (if any), LDAPS
requirements, SSO requirements, sharing targets, replication
regions, password policy settings, tags.

### Natural language

Any of these routes to the same skill:

- "create a Managed Microsoft AD Enterprise directory"
- "deploy Simple AD for dev"
- "set up an AD Connector to on-prem"
- "create a forest trust with onprem.example.com"
- "enable LDAPS on my directory"
- "share my directory with account 999999999999"

### CLI routing

```bash
node cli/bin/cli.js route "create a managed microsoft ad"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The orchestrator routes to it when the user wants to
create or configure AWS Directory Service directories. The output
checklist feeds into verification pipelines and downstream audit
skills.

## Example

```
You: /aws:deploy-directory-service

     Create a Managed Microsoft AD Enterprise directory in
     us-east-1. VPC vpc-aaa11122, subnets subnet-aaa111 and
     subnet-bbb222. Two-way forest trust with onprem.example.com.
     Enable LDAPS with AWS PCA cert. Connect IAM Identity Center.

Skill:
  DIRECTORY_SERVICE: d-aaa111222 (ManagedMicrosoftAD, Enterprise)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Directory type: Managed Microsoft AD
    [✓] Edition: Enterprise
    [✓] Trust: Forest Two-Way to onprem.example.com
    [✓] LDAPS: enabled (AWS PCA, expires 2026-12-01)
    [✓] SSO: IAM Identity Center connected
  VERIFICATION_COMMANDS:
    aws ds describe-directories --directory-ids d-aaa111222 --region us-east-1
    aws ds describe-trusts --directory-id d-aaa111222 --region us-east-1
```

## References

- Skill definition: `skills/directory-service-deployer/SKILL.md`
- Trust and LDAPS guide: `skills/directory-service-deployer/references/trust-and-ldaps.md`
- SSO and sharing guide: `skills/directory-service-deployer/references/sso-and-sharing.md`
- Eval suite: `skills/directory-service-deployer/evals/evals.json`
