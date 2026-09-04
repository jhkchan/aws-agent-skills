---
name: skill-catalog
description: 'Indexes all 409 eval-backed AWS CloudOps skills in this repo for precise @skills-protocol invocation: 13 family tables mapping every skill to its exact gh: path, task type, and one-line description. Use when an agent needs to find, select, or call a specific AWS CloudOps skill by path, when browsing the repo root is refused by the 128-skill menu rule, or when unsure which of the 409 skills handles a task. Triggers: skill catalog, find skill, which skill, select skill, list skills, skill index, precise skill path.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md; @skills-protocol clients (atskills CLI). No AWS credentials needed.
metadata:
  domain: aws-cloudops
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  family: Governance
  verdict_shape: PATH_RESOLVED | FAMILY_LISTED
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
---
# Skill catalog — precise discovery for 409 AWS CloudOps skills

This repo ships **409 eval-backed skills** across 13 service families. This catalog is the
precise-discovery surface for agent runtimes that use the `@skills` protocol (atskills.one).

## Why a catalog (the 128-skill rule)

The `@skills` protocol refuses to enumerate a directory menu with more than **128 skills**
(SKILLS.md §1.5). `skills/` here holds 409, so browsing the repo root is refused by design.
Direct references are unaffected — every skill below is one precise call away. Point agents
here first; the family tables route to complete per-skill listings.

## Precise-call syntax

```
@skills:gh:jhkchan/aws-agent-skills/skills/<skill-name>
```

Examples:
- `@skills:gh:jhkchan/aws-agent-skills/skills/s3-public-access-auditor` — audit buckets for public exposure
- `@skills:gh:jhkchan/aws-agent-skills/skills/lambda-invocation-troubleshooter` — diagnose Lambda failures
- `@skills:gh:jhkchan/aws-agent-skills/skills/vpc-peering-deployer` — provision a VPC peering connection

Paths are case-sensitive lowercase kebab-case and match each skill's `name` exactly.

## Family index

| Family | Skills | Look here for | Full listing |
|---|---|---|---|
| Security | 52 | IAM, KMS, Secrets Manager, GuardDuty, Security Hub, WAF, certificates, detections | [by-family/security.md](references/by-family/security.md) |
| Compute | 44 | EC2, Lambda, ECS, EKS, Batch, Auto Scaling, rightsizing, cold starts | [by-family/compute.md](references/by-family/compute.md) |
| Management | 43 | CloudWatch, CloudTrail, SSM, X-Ray, observability, patching, sessions | [by-family/management.md](references/by-family/management.md) |
| Analytics | 41 | Athena, Glue, Kinesis, OpenSearch, Redshift, QuickSight, MWAA | [by-family/analytics.md](references/by-family/analytics.md) |
| Storage | 40 | S3 (all features), EBS, EFS, FSx, Backup, Storage Gateway, Transfer Family | [by-family/storage.md](references/by-family/storage.md) |
| Networking | 39 | VPC, Route 53, CloudFront, ELB, Transit Gateway, VPN, endpoints, WAF edge | [by-family/networking.md](references/by-family/networking.md) |
| AppIntegration | 33 | SQS, SNS, EventBridge, Step Functions, API Gateway, MQ, App Config | [by-family/appintegration.md](references/by-family/appintegration.md) |
| Databases | 31 | RDS, Aurora, DynamoDB, ElastiCache, DocumentDB, Neptune, QLDB, Keyspaces | [by-family/databases.md](references/by-family/databases.md) |
| Governance | 29 | Organizations, Control Tower, Config, tags, accounts, policies, quotas | [by-family/governance.md](references/by-family/governance.md) |
| DevTools | 24 | CodeCommit, CodeBuild, CodePipeline, CodeArtifact, Cloud9, SAR | [by-family/devtools.md](references/by-family/devtools.md) |
| AI/ML | 16 | Bedrock, SageMaker, Comprehend, Rekognition, Transcribe, Polly, Textract | [by-family/ai-ml.md](references/by-family/ai-ml.md) |
| FinOps | 12 | Budgets, Cost Explorer, CUR, anomaly detection, cost optimization hub | [by-family/finops.md](references/by-family/finops.md) |
| Migration | 5 | DMS, Migration Hub, Snowball, DataSync, transfer | [by-family/migration.md](references/by-family/migration.md) |
| **Total** | **409** | | |

## Selection rules for agents

1. Match the user's task type first: audit / deploy / troubleshoot / optimize / operate / automate
   (each listing row carries the task type).
2. Match the AWS service family second.
3. Prefer the skill whose one-liner names the exact operation; load its SKILL.md only then
   (progressive disclosure — descriptions are the activation contract).
4. Never guess a path: every path in the family listings is exact and copy-pasteable.

## References (load on demand)

- [by-family/ai-ml.md](references/by-family/ai-ml.md) — all 16 AI/ML skills with precise paths
- [by-family/analytics.md](references/by-family/analytics.md) — all 41 Analytics skills with precise paths
- [by-family/appintegration.md](references/by-family/appintegration.md) — all 33 AppIntegration skills with precise paths
- [by-family/compute.md](references/by-family/compute.md) — all 44 Compute skills with precise paths
- [by-family/databases.md](references/by-family/databases.md) — all 31 Databases skills with precise paths
- [by-family/devtools.md](references/by-family/devtools.md) — all 24 DevTools skills with precise paths
- [by-family/finops.md](references/by-family/finops.md) — all 12 FinOps skills with precise paths
- [by-family/governance.md](references/by-family/governance.md) — all 29 Governance skills with precise paths
- [by-family/management.md](references/by-family/management.md) — all 43 Management skills with precise paths
- [by-family/migration.md](references/by-family/migration.md) — all 5 Migration skills with precise paths
- [by-family/networking.md](references/by-family/networking.md) — all 39 Networking skills with precise paths
- [by-family/security.md](references/by-family/security.md) — all 52 Security skills with precise paths
- [by-family/storage.md](references/by-family/storage.md) — all 40 Storage skills with precise paths

## Domain

AWS CloudOps agent skills — https://github.com/jhkchan/aws-agent-skills
