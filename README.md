# aws-agent-skills

> **Repository:** [jhkchan/aws-agent-skills](https://github.com/jhkchan/aws-agent-skills)
> · License: **Apache-2.0** · Maintainer: **Jacky Chan, AWS Community Builder (ML & GenAI)**
> · A solo, community-driven project.

**409 eval-backed AWS CloudOps agent skills** across **13 AWS service families** and **6 task types** (audit · deploy · troubleshoot · optimize · operate · automate) — every skill ships with a committed, median-of-3-judge-scored eval scorecard. Measured, not asserted. Built on the [softaworks skill-judge](https://github.com/softaworks/agent-toolkit/tree/main/skills/skill-judge) 8-dimension rubric, with co-located structured evals (cases + baselines + delta comparison) on every skill.

---

## Why eval-backed?

Every existing AWS agent-skill repo — `aws/agent-toolkit-for-aws` (140 skills), `itsmostafa/aws-agent-skills` (18), `softaworks/agent-toolkit` — ships `SKILL.md` + references and **claims** "thorough evals" with **zero published artifacts**. This repo makes the eval-backed contract **structural**: every skill carries a co-located `eval/test-cases.yaml` that produces a per-dimension scorecard when run through the shared Python harness. The scorecard is committed. The grade is real.

---

## Installation

### Method 1 — Agent runtime (Claude Code, Cursor, Windsurf)

```bash
git clone https://github.com/jhkchan/aws-agent-skills.git

# Copy the skills you want into your agent's skills directory.
# For Claude Code:
cp -r aws-agent-skills/skills/s3-public-access-auditor ~/.claude/skills/

# Or install ALL 409 skills at once:
cp -r aws-agent-skills/skills/* ~/.claude/skills/
```

### Method 2 — Marketplace / plugin manifest

The repo includes `.claude-plugin/marketplace.json` for agent runtimes that support plugin manifests. Point your runtime at this repo's root.

### Method 3 — Use the CLI to discover and route

```bash
git clone https://github.com/jhkchan/aws-agent-skills.git
cd aws-agent-skills
node cli/bin/cli.js list          # list all skills + the orchestrator
node cli/bin/cli.js list --task-type deploy     # filter by task type
node cli/bin/cli.js route "audit my S3 buckets for public access"  # route a prompt
node cli/bin/cli.js route "deploy a secure VPC"  # deploy routing
node cli/bin/cli.js route "why is my Lambda timing out"  # troubleshoot routing
node cli/bin/cli.js status        # coverage + eval status summary
```

---

## Calling a skill precisely (`@skills` protocol)

This repo is a `@skills`-compatible skill source (atskills.one):

```
@skills:gh:jhkchan/aws-agent-skills/skills/<skill-name>
```

409 skills > the protocol's 128-skill browsing limit, so point agents at the catalog first:
`@skills:gh:jhkchan/aws-agent-skills/skills/skill-catalog` — 13 family tables with exact
paths, task types, and one-liners. See [SKILL_GOVERNANCE.md](SKILL_GOVERNANCE.md) for the
full protocol audit and rules.

## Quickstart

### Audit something right now

Once a skill is installed in your agent runtime, just describe the task:

```
Audit my S3 buckets for public access.
```

The skill activates, asks for the bucket configs (or fetches them via `aws s3api`), and produces structured verdicts:

```text
BUCKET: app-data-prod
VERDICT: SAFE
REASON: S3 Block Public Access is fully enabled (all 4 settings).
REMEDIATION: None required.

BUCKET: public-assets-cdn
VERDICT: PUBLIC
REASON: BPA is OFF. Bucket policy grants s3:GetObject to Principal "*" with no condition.
REMEDIATION: Enable BPA (all 4 settings). Use CloudFront + OAC if public CDN is intended.
```

### Use the orchestrator for a full CloudOps audit

```
Run a full CloudOps security audit across my AWS account.
```

The `aws-orchestrator` skill routes the request across relevant auditors (S3, IAM, EC2, GuardDuty, KMS, etc.) in a 4-phase pipeline: **Assess > Audit > Prioritize > Remediate**.

### Beyond auditing — deploy, troubleshoot, optimize

The repo now covers **6 task types**, not just audit:

| Task type | What it does | Example skills |
|---|---|---|
| **audit** | Assess posture, compliance, configuration drift | `s3-public-access-auditor`, `iam-least-privilege-advisor` |
| **deploy** | Provision with correct defaults and best practices | `s3-secure-bucket-deployer`, `lambda-function-deployer`, `vpc-network-deployer` |
| **troubleshoot** | Diagnose and resolve operational issues | `iam-permission-troubleshooter`, `rds-connectivity-troubleshooter` |
| **optimize** | Reduce cost or improve performance | `ec2-rightsizing-optimizer`, `s3-lifecycle-optimizer` |
| **operate** | Day-2 operations (backup, restore, failover) | `rds-backup-restore-operator` |
| **automate** | Workflow/pipeline patterns | `securityhub-remediation-automator`, `tag-compliance-automator`, `drift-detection-automator` |

```
Deploy a secure S3 bucket with encryption and lifecycle rules.
```

The `s3-secure-bucket-deployer` walks through the 10-step provisioning procedure and emits a READY_TO_DEPLOY checklist.

### Coverage matrix

| Family | Skills | | Family | Skills |
|---|---|---|---|---|
| Security | 51 | | AppIntegration | 34 |
| Compute | 43 | | Databases | 31 |
| Management | 42 | | Governance | 30 |
| Analytics | 41 | | DevTools | 24 |
| Storage | 40 | | AI/ML | 16 |
| Networking | 38 | | FinOps | 13 |
| | | | Migration | 5 |

| Task type | Skills | | Task type | Skills |
|---|---|---|---|---|
| deploy | 155 | | optimize | 41 |
| audit | 80 | | operate | 40 |
| troubleshoot | 58 | | automate | 31 |

### Slash commands

Each skill has a slash command (in `commands/aws/`):

```
/aws:audit-s3-public-access
/aws:audit-iam-least-privilege
/aws:audit-ec2-security-group
/aws:audit-guardduty-findings
/aws:deploy-s3-secure-bucket-deployer
/aws:deploy-vpc-network-deployer
/aws:troubleshoot-iam-permission-troubleshooter
/aws:optimize-ec2-rightsizing-optimizer
/aws:operate-rds-backup-restore-operator
... (380+ commands total)
```

---

## Usage examples

### Example 1 — IAM policy review

**Prompt:** `Review this IAM policy for least-privilege violations.`

```text
POLICY: app-backend-role-policy
VERDICT: OVERPERMISSIVE
RISK: CRITICAL
REASON: Statement 1 grants iam:PassRole on Resource "*" — privilege escalation vector.
REMEDIATION: Scope iam:PassRole to specific service-linked roles. Remove wildcard Resource.
```

### Example 2 — Lambda runtime deprecation

**Prompt:** `Check if any of my Lambda functions use deprecated runtimes.`

```text
FUNCTION: data-processor
VERDICT: DEPRECATED_RUNTIME
RISK: HIGH
REASON: Runtime python3.9 reaches end-of-support 2025-10. AWS will block updates after 2026-01.
REMEDIATION: Upgrade to python3.13. Test with sam build && sam local invoke.
```

### Example 3 — Bedrock guardrail coverage

**Prompt:** `Audit my Bedrock guardrails for coverage gaps.`

```text
MODEL: anthropic.claude-sonnet-5
VERDICT: INCOMPLETE_COVERAGE
REASON: Guardrail gr-abc123 exists but does not cover this model.
REMEDIATION: Associate the guardrail with this model via update-guardrail.
```

See `skills/<name>/examples/` for full multi-finding walkthroughs per skill.

---

## Skills

<!-- Auto-generated by eval/generate_readme_table.py -- do not edit by hand. -->
<!-- To update: python3 eval/generate_readme_table.py -->
<!-- BEGIN EVAL SCORECARD TABLE -->
| Skill | Model | Score | Grade | Verdicts | Latency | Tokens |
|---|---|---|---|---|---|---|
| accessanalyzer-finding-triage | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 9.4s | 56729 |
| account-factory-deployer | amazon.nova-pro-v1:0 | 104/120 | B | 4/5 | 28.4s | 52216 |
| acm-certificate-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 4/5 | 8.9s | 39946 |
| acm-certificate-expiry-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 12.0s | 37462 |
| acm-certificate-monitor-operator | amazon.nova-pro-v1:0 | 108/120 | A | 2/5 | 15.7s | 47941 |
| acm-private-ca-deployer | amazon.nova-pro-v1:0 | 103/120 | B | 5/5 | 9.5s | 49145 |
| alb-5xx-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 27.8s | 54221 |
| alb-unhealthy-target-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 12.6s | 56762 |
| amazon-mq-broker-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 3/5 | 17.2s | 46807 |
| amplify-app-deployer | amazon.nova-pro-v1:0 | 104/120 | B | 5/5 | 5.2s | 43498 |
| amplify-branch-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 12.6s | 44736 |
| apigateway-5xx-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 0/5 | 21.4s | 54610 |
| apigateway-http-api-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 13.5s | 50055 |
| apigateway-http-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 0/5 | 15.3s | 45003 |
| apigateway-resource-policy-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 9.6s | 35471 |
| apigateway-rest-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 15.8s | 48821 |
| apigateway-throttle-optimizer | amazon.nova-pro-v1:0 | 101/120 | B | 5/5 | 11.5s | 45943 |
| apigateway-websocket-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 14.1s | 54765 |
| appconfig-deployer | amazon.nova-pro-v1:0 | 99/120 | B | 4/5 | 8.2s | 40587 |
| appconfig-deployment-operator | amazon.nova-pro-v1:0 | 99/120 | B | 2/5 | 20.4s | 45698 |
| appmesh-deployer | amazon.nova-pro-v1:0 | 110/120 | A | 4/5 | 25.8s | 44770 |
| appmesh-virtual-service-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 13.3s | 46928 |
| apprunner-autoscaling-optimizer | amazon.nova-pro-v1:0 | 104/120 | B | 4/5 | 14.6s | 45763 |
| apprunner-service-deployer | amazon.nova-pro-v1:0 | 99/120 | B | 5/5 | 24.2s | 40834 |
| athena-query-failure-troubleshooter | amazon.nova-pro-v1:0 | 110/120 | A | 0/5 | 12.6s | 61307 |
| athena-query-optimizer | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 30.9s | 40822 |
| athena-workgroup-auditor | amazon.nova-pro-v1:0 | 114/120 | A | 6/6 | 8.6s | 49642 |
| auditmanager-assessment-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 12.6s | 50433 |
| aurora-cost-optimizer | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 22.8s | 52349 |
| aurora-failover-operator | amazon.nova-pro-v1:0 | 109/120 | A | 3/5 | 15.5s | 46622 |
| auto-remediation-automator | amazon.nova-pro-v1:0 | 111/120 | A | 1/5 | 14.3s | 51136 |
| autoscaling-group-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 18.9s | 39803 |
| autoscaling-lifecycle-operator | amazon.nova-pro-v1:0 | 104/120 | B | 4/5 | 12.0s | 37738 |
| autoscaling-policy-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 6.4s | 46531 |
| backup-audit-automator | amazon.nova-pro-v1:0 | 101/120 | B | 2/5 | 4.8s | 35480 |
| backup-compliance-automator | amazon.nova-pro-v1:0 | 103/120 | B | 0/5 | 35.8s | 49013 |
| backup-cross-region-operator | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 18.0s | 43394 |
| backup-plan-auditor | amazon.nova-pro-v1:0 | 115/120 | A | 6/6 | 8.5s | 30595 |
| backup-schedule-automator | amazon.nova-pro-v1:0 | 100/120 | B | 0/5 | 27.4s | 38388 |
| backup-vault-compliance-automator | amazon.nova-pro-v1:0 | 107/120 | B | 0/5 | 11.8s | 42369 |
| backup-vault-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 3/5 | 13.4s | 37840 |
| backup-vault-operator | amazon.nova-pro-v1:0 | 103/120 | B | 3/5 | 15.1s | 60013 |
| batch-compute-environment-deployer | amazon.nova-pro-v1:0 | 104/120 | B | 5/5 | 13.0s | 45149 |
| bedrock-guardrail-coverage-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 5.1s | 31762 |
| bedrock-guardrail-deployer | amazon.nova-pro-v1:0 | 98/120 | B | 0/5 | 8.1s | 46004 |
| bedrock-model-access-inventory | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 14.4s | 35705 |
| bedrock-model-cost-optimizer | amazon.nova-pro-v1:0 | 112/120 | A | 1/5 | 15.7s | 48169 |
| billing-account-auditor | amazon.nova-pro-v1:0 | 114/120 | A | 6/6 | 13.4s | 37235 |
| budget-action-automator | amazon.nova-pro-v1:0 | 109/120 | A | 1/5 | 39.2s | 56060 |
| budget-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 2/5 | 4.7s | 47221 |
| budgets-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 12.2s | 37761 |
| ce-cost-anomaly-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 30.5s | 36151 |
| certificate-renewal-automator | amazon.nova-pro-v1:0 | 106/120 | B | 0/5 | 14.4s | 46854 |
| cicd-pipeline-automator | amazon.nova-pro-v1:0 | 110/120 | A | 5/5 | 16.4s | 63346 |
| clb-to-alb-migration-operator | amazon.nova-pro-v1:0 | 111/120 | A | 4/5 | 11.9s | 45791 |
| cleanrooms-collaboration-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 20.3s | 47219 |
| client-vpn-endpoint-deployer | amazon.nova-pro-v1:0 | 102/120 | B | 5/5 | 12.9s | 42143 |
| cloud9-environment-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 3/5 | 11.3s | 41308 |
| cloudformation-cfn-lint-operator | amazon.nova-pro-v1:0 | 101/120 | B | 5/5 | 12.8s | 41156 |
| cloudformation-drift-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 24.0s | 45911 |
| cloudformation-stack-rollback-troubleshooter | amazon.nova-pro-v1:0 | 104/120 | B | 0/5 | 8.5s | 38107 |
| cloudformation-stack-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 3/5 | 13.7s | 48363 |
| cloudformation-stackset-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 8.9s | 41767 |
| cloudfront-502-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 11.5s | 39491 |
| cloudfront-cache-troubleshooter | amazon.nova-pro-v1:0 | 110/120 | A | 5/5 | 12.6s | 43563 |
| cloudfront-cost-optimizer | amazon.nova-pro-v1:0 | 112/120 | A | 5/5 | 9.8s | 72815 |
| cloudfront-distribution-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 13.3s | 39728 |
| cloudfront-distribution-deployer | amazon.nova-pro-v1:0 | 111/120 | A | 0/5 | 10.2s | 49278 |
| cloudfront-invalidation-operator | amazon.nova-pro-v1:0 | 112/120 | A | 4/5 | 6.3s | 40772 |
| cloudfront-keyvaluestore-deployer | amazon.nova-pro-v1:0 | 110/120 | A | 3/5 | 8.7s | 52332 |
| cloudfront-origin-access-control-deployer | amazon.nova-pro-v1:0 | 113/120 | A | 4/5 | 8.4s | 50022 |
| cloudfront-response-headers-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 33.7s | 48177 |
| cloudhsm-cluster-deployer | amazon.nova-pro-v1:0 | 107/120 | B | 2/5 | 10.4s | 53997 |
| cloudhsm-cluster-posture-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 5.9s | 35489 |
| cloudtrail-alert-automator | amazon.nova-pro-v1:0 | 107/120 | B | 3/5 | 9.7s | 49610 |
| cloudtrail-cost-optimizer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 43.3s | 50346 |
| cloudtrail-gap-troubleshooter | amazon.nova-pro-v1:0 | 101/120 | B | 5/5 | 12.1s | 40463 |
| cloudtrail-lake-operator | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 16.2s | 54032 |
| cloudtrail-lake-query-deployer | amazon.nova-pro-v1:0 | 99/120 | B | 3/5 | 17.0s | 40842 |
| cloudtrail-missing-events-troubleshooter | amazon.nova-pro-v1:0 | 104/120 | B | 0/0 | 18.6s | 38923 |
| cloudtrail-org-trail-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 9.7s | 38562 |
| cloudwatch-alarm-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 39.2s | 36433 |
| cloudwatch-alarm-notification-automator | amazon.nova-pro-v1:0 | 104/120 | B | 4/5 | 6.9s | 42957 |
| cloudwatch-alarm-operator | amazon.nova-pro-v1:0 | 111/120 | A | 3/5 | 13.2s | 40696 |
| cloudwatch-alarm-troubleshooter | amazon.nova-pro-v1:0 | 111/120 | A | 0/5 | 8.7s | 49894 |
| cloudwatch-anomaly-detector-deployer | amazon.nova-pro-v1:0 | 107/120 | B | 3/5 | 9.9s | 51216 |
| cloudwatch-application-signals-deployer | amazon.nova-pro-v1:0 | 99/120 | B | 5/5 | 11.4s | 40203 |
| cloudwatch-application-signals-operator | amazon.nova-pro-v1:0 | 104/120 | B | 1/5 | 7.3s | 46948 |
| cloudwatch-cross-account-observability-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 2/5 | 14.3s | 43674 |
| cloudwatch-dashboard-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 15.1s | 45281 |
| cloudwatch-dashboards-operator | amazon.nova-pro-v1:0 | 106/120 | B | 4/5 | 13.3s | 47615 |
| cloudwatch-logs-cost-optimizer | amazon.nova-pro-v1:0 | 103/120 | B | 4/5 | 13.1s | 55159 |
| cloudwatch-logs-insights-troubshooter | amazon.nova-pro-v1:0 | 105/120 | B | 5/5 | 13.4s | 43201 |
| cloudwatch-logs-not-ingesting-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 14.1s | 45480 |
| cloudwatch-logs-retention-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 29.7s | 42221 |
| cloudwatch-metric-stream-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 4/5 | 9.0s | 40901 |
| cloudwatch-metrics-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 27.3s | 50214 |
| cloudwatch-rum-deployer | amazon.nova-pro-v1:0 | 96/120 | B | 2/5 | 14.5s | 50044 |
| cloudwatch-synthetics-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 11.3s | 41470 |
| codeartifact-domain-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 4/5 | 16.0s | 45156 |
| codeartifact-repository-deployer | amazon.nova-pro-v1:0 | 100/120 | B | 4/5 | 11.5s | 40220 |
| codebuild-build-troubleshooter | amazon.nova-pro-v1:0 | 106/120 | B | 0/5 | 8.4s | 46863 |
| codebuild-project-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 16.4s | 49703 |
| codecommit-repository-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 8.2s | 32563 |
| codecommit-repository-deployer | amazon.nova-pro-v1:0 | 102/120 | B | 4/5 | 10.0s | 49919 |
| codedeploy-deployment-group-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 23.8s | 39309 |
| codepipeline-failure-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 13.4s | 47460 |
| codepipeline-pipeline-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 13.7s | 39910 |
| codepipeline-v2-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 17.9s | 51505 |
| cognito-auth-troubleshooter | amazon.nova-pro-v1:0 | 111/120 | A | 0/5 | 7.0s | 67677 |
| cognito-identity-pool-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 11.7s | 40859 |
| cognito-idp-user-pool-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 6.8s | 41140 |
| cognito-user-pool-deployer | amazon.nova-pro-v1:0 | 107/120 | B | 4/5 | 10.5s | 48126 |
| comprehend-classifier-deployer | amazon.nova-pro-v1:0 | 104/120 | B | 5/5 | 13.5s | 48195 |
| compute-optimizer-findings-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 17.8s | 35720 |
| config-aggregator-deployer | amazon.nova-pro-v1:0 | 98/120 | B | 4/5 | 14.5s | 41086 |
| config-recorder-coverage-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 35.6s | 43031 |
| config-rule-compliance-automator | amazon.nova-pro-v1:0 | 109/120 | A | 0/5 | 8.1s | 37223 |
| config-rule-deployer | amazon.nova-pro-v1:0 | 107/120 | B | 5/5 | 13.9s | 36535 |
| connect-instance-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 2/5 | 13.7s | 53043 |
| controltower-control-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 23.1s | 33282 |
| cost-anomaly-detection-automator | amazon.nova-pro-v1:0 | 106/120 | B | 1/5 | 28.4s | 45954 |
| cost-anomaly-response-automator | amazon.nova-pro-v1:0 | 104/120 | B | 0/5 | 10.3s | 42763 |
| cost-optimization-hub-recommendations-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 12.3s | 37941 |
| cur-automation-automator | amazon.nova-pro-v1:0 | 107/120 | B | 2/5 | 14.6s | 43998 |
| cur-cost-usage-report-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 7.0s | 38402 |
| data-transfer-optimizer | amazon.nova-pro-v1:0 | 114/120 | A | 2/5 | 15.7s | 75706 |
| dataexchange-dataset-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 34.3s | 46150 |
| datasync-task-operator | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 5.4s | 54284 |
| datazone-domain-deployer | amazon.nova-pro-v1:0 | 104/120 | B | 4/5 | 5.6s | 59228 |
| detective-investigation-coverage-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 13.5s | 34135 |
| devops-guru-troubleshooter | amazon.nova-pro-v1:0 | 102/120 | B | 3/5 | 8.4s | 38859 |
| directconnect-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 17.7s | 52075 |
| directory-service-deployer | amazon.nova-pro-v1:0 | 107/120 | B | 5/5 | 11.0s | 39472 |
| dlm-lifecycle-policy-auditor | amazon.nova-pro-v1:0 | 112/120 | A | 6/6 | 6.2s | 41975 |
| dms-endpoint-deployer | amazon.nova-pro-v1:0 | 102/120 | B | 3/5 | 10.5s | 40580 |
| dms-replication-task-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 18.3s | 39911 |
| dms-task-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 6.6s | 44785 |
| documentdb-cluster-deployer | amazon.nova-pro-v1:0 | 103/120 | B | 5/5 | 4.6s | 47582 |
| dr-failover-automator | amazon.nova-pro-v1:0 | 102/120 | B | 0/5 | 8.4s | 45629 |
| drift-detection-automator | amazon.nova-pro-v1:0 | 106/120 | B | 2/5 | 8.6s | 42634 |
| dynamodb-autoscaling-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 8.1s | 50983 |
| dynamodb-backup-operator | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 9.9s | 47165 |
| dynamodb-capacity-optimizer | amazon.nova-pro-v1:0 | 97/120 | B | 5/5 | 11.9s | 53027 |
| dynamodb-global-tables-operator | amazon.nova-pro-v1:0 | 110/120 | A | 4/5 | 6.8s | 43494 |
| dynamodb-table-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 12.8s | 38416 |
| dynamodb-table-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 17.1s | 59731 |
| dynamodb-throttling-optimizer | amazon.nova-pro-v1:0 | 103/120 | B | 5/5 | 17.4s | 43790 |
| dynamodb-throttling-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 14.0s | 50993 |
| ebs-volume-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 16.0s | 35713 |
| ebs-volume-optimizer | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 16.9s | 70173 |
| ec2-backup-operator | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 11.1s | 56997 |
| ec2-instance-recovery-operator | amazon.nova-pro-v1:0 | 107/120 | B | 4/5 | 25.1s | 43194 |
| ec2-instance-rightsizer | amazon.nova-pro-v1:0 | 103/120 | B | 5/5 | 14.3s | 52031 |
| ec2-launch-template-deployer | amazon.nova-pro-v1:0 | 105/120 | B | 2/5 | 15.1s | 42525 |
| ec2-reserved-capacity-optimizer | amazon.nova-pro-v1:0 | 102/120 | B | 3/5 | 12.7s | 39957 |
| ec2-rightsizing-optimizer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 14.9s | 65548 |
| ec2-security-group-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 5/5 | 11.5s | 38372 |
| ec2-spot-fleet-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 8.3s | 39476 |
| ec2-spot-interruption-operator | amazon.nova-pro-v1:0 | 107/120 | B | 3/5 | 10.7s | 48758 |
| ecr-push-pull-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 11.8s | 48492 |
| ecr-replication-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 2/5 | 9.6s | 38485 |
| ecr-repository-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 12.4s | 46409 |
| ecs-cluster-autoscaling-optimizer | amazon.nova-pro-v1:0 | 111/120 | A | 5/5 | 14.8s | 49417 |
| ecs-fargate-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 19.7s | 37991 |
| ecs-task-cost-optimizer | amazon.nova-pro-v1:0 | 103/120 | B | 5/5 | 11.7s | 51013 |
| ecs-task-definition-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 13.9s | 45015 |
| ecs-task-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 3/5 | 9.4s | 43291 |
| efs-access-point-deployer | amazon.nova-pro-v1:0 | 107/120 | B | 2/5 | 15.5s | 45719 |
| efs-filesystem-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 11.6s | 38429 |
| eks-add-on-deployer | amazon.nova-pro-v1:0 | 99/120 | B | 4/5 | 14.1s | 47574 |
| eks-autoscaling-automator | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 11.4s | 42120 |
| eks-cluster-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 11.7s | 34838 |
| eks-cost-optimizer | amazon.nova-pro-v1:0 | 107/120 | B | 3/5 | 15.9s | 43282 |
| eks-hybrid-node-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 11.9s | 42416 |
| eks-nodegroup-troubleshooter | amazon.nova-pro-v1:0 | 104/120 | B | 0/5 | 6.2s | 36532 |
| eks-pod-troubleshooter | amazon.nova-pro-v1:0 | 110/120 | A | 4/5 | 16.1s | 55994 |
| eks-security-optimizer | amazon.nova-pro-v1:0 | 104/120 | B | 5/5 | 15.8s | 44904 |
| eks-upgrade-operator | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 11.8s | 44688 |
| elastic-beanstalk-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 26.4s | 49334 |
| elastic-beanstalk-environment-optimizer | amazon.nova-pro-v1:0 | 100/120 | B | 3/5 | 16.1s | 47010 |
| elasticache-cache-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 10.9s | 68137 |
| elasticache-cluster-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 0/0 | 21.3s | 37454 |
| elasticache-cost-optimizer | amazon.nova-pro-v1:0 | 110/120 | A | 0/5 | 25.3s | 49189 |
| elb-cost-optimizer | amazon.nova-pro-v1:0 | 101/120 | B | 4/5 | 14.9s | 41685 |
| elbv2-load-balancer-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 8.6s | 47542 |
| emr-cluster-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 0/6 | 12.2s | 33961 |
| emr-serverless-deployer | amazon.nova-pro-v1:0 | 98/120 | B | 3/5 | 14.8s | 40535 |
| event-driven-automator | amazon.nova-pro-v1:0 | 109/120 | A | 3/5 | 13.6s | 44835 |
| eventbridge-bus-policy-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 12.9s | 40249 |
| eventbridge-pipe-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 12.1s | 54732 |
| eventbridge-rule-deployer | amazon.nova-pro-v1:0 | 110/120 | A | 1/5 | 17.3s | 52693 |
| eventbridge-rule-not-firing-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 12.1s | 60138 |
| eventbridge-scheduler-deployer | amazon.nova-pro-v1:0 | 107/120 | B | 4/5 | 13.2s | 45637 |
| fargate-cost-optimizer | amazon.nova-pro-v1:0 | 102/120 | B | 4/5 | 15.9s | 41637 |
| firehose-delivery-stream-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 5.2s | 43387 |
| firehose-delivery-stream-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 4/5 | 8.6s | 39001 |
| firewall-manager-compliance-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 16.8s | 53101 |
| firewall-manager-deployer | amazon.nova-pro-v1:0 | 112/120 | A | 4/5 | 13.4s | 45698 |
| fis-experiment-deployer | amazon.nova-pro-v1:0 | 103/120 | B | 4/5 | 7.1s | 41699 |
| fis-template-deployer | amazon.nova-pro-v1:0 | 104/120 | B | 5/5 | 8.9s | 40919 |
| fsx-filesystem-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 4/5 | 6.8s | 41043 |
| globalaccelerator-deployer | amazon.nova-pro-v1:0 | 107/120 | B | 0/5 | 15.9s | 51559 |
| glue-crawler-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 9.3s | 42050 |
| glue-crawler-job-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 35.0s | 48227 |
| glue-job-failure-troubleshooter | amazon.nova-pro-v1:0 | 110/120 | A | 4/5 | 22.5s | 44555 |
| glue-job-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 13.4s | 45443 |
| grafana-dashboard-deployer | amazon.nova-pro-v1:0 | 103/120 | B | 4/5 | 16.8s | 49347 |
| grafana-data-source-deployer | amazon.nova-pro-v1:0 | 99/120 | B | 4/5 | 26.6s | 40745 |
| greengrass-component-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 7.5s | 52282 |
| guardduty-finding-automator | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 8.7s | 44299 |
| guardduty-finding-investigator | amazon.nova-pro-v1:0 | 109/120 | A | 0/5 | 7.6s | 45534 |
| guardduty-finding-severity-triage | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 12.3s | 55940 |
| health-event-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 12.4s | 42780 |
| health-event-automator | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 6.8s | 48973 |
| iac-template-automator | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 20.6s | 58312 |
| iam-key-rotation-automator | amazon.nova-pro-v1:0 | 104/120 | B | 1/5 | 13.0s | 39189 |
| iam-least-privilege-advisor | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 7.8s | 33835 |
| iam-permission-troubleshooter | amazon.nova-pro-v1:0 | 112/120 | A | 5/5 | 14.4s | 50894 |
| iam-role-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 20.9s | 54672 |
| incident-response-automator | amazon.nova-pro-v1:0 | 109/120 | A | 0/5 | 4.9s | 55975 |
| inspector2-automation-automator | amazon.nova-pro-v1:0 | 109/120 | A | 0/5 | 9.5s | 49006 |
| inspector2-coverage-finding-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 17.3s | 52550 |
| inspector2-coverage-operator | amazon.nova-pro-v1:0 | 102/120 | B | 5/5 | 6.5s | 42054 |
| inspector2-finding-troubleshooter | amazon.nova-pro-v1:0 | 107/120 | B | 3/5 | 25.2s | 46527 |
| iot-core-thing-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 2/5 | 14.0s | 41599 |
| kafka-connect-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 6.4s | 39678 |
| kafka-msk-lag-troubleshooter | amazon.nova-pro-v1:0 | 110/120 | A | 0/5 | 16.6s | 63795 |
| kafka-msk-troubleshooter | amazon.nova-pro-v1:0 | 106/120 | B | 4/5 | 4.5s | 39312 |
| keyspaces-keyspace-deployer | amazon.nova-pro-v1:0 | 103/120 | B | 3/5 | 12.5s | 50970 |
| kinesis-analytics-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 5/5 | 6.6s | 41385 |
| kinesis-firehose-troubleshooter | amazon.nova-pro-v1:0 | 102/120 | B | 5/5 | 12.1s | 55992 |
| kinesis-stream-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 27.1s | 42232 |
| kinesis-stream-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 10.7s | 55532 |
| kms-key-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 4/5 | 4.8s | 37611 |
| kms-key-policy-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 17.2s | 49516 |
| kms-key-rotation-operator | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 4.6s | 45796 |
| kms-key-rotation-optimizer | amazon.nova-pro-v1:0 | 101/120 | B | 3/5 | 13.3s | 49806 |
| lakeformation-data-lake-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 13.1s | 43103 |
| lakeformation-permissions-deployer | amazon.nova-pro-v1:0 | 103/120 | B | 0/5 | 11.9s | 40915 |
| lambda-alias-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 4/5 | 9.1s | 37587 |
| lambda-cold-start-optimizer | amazon.nova-pro-v1:0 | 105/120 | B | 5/5 | 9.4s | 46380 |
| lambda-cost-optimizer | amazon.nova-pro-v1:0 | 101/120 | B | 5/5 | 17.9s | 44547 |
| lambda-function-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 9.6s | 49830 |
| lambda-function-url-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 9.6s | 49093 |
| lambda-invocation-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 10.9s | 67093 |
| lambda-layer-deployer | amazon.nova-pro-v1:0 | 104/120 | B | 4/5 | 31.7s | 40094 |
| lambda-memory-optimizer | amazon.nova-pro-v1:0 | 105/120 | B | 5/5 | 23.0s | 50069 |
| lambda-runtime-deprecation-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 15.4s | 45863 |
| lambda-timeout-troubleshooter | amazon.nova-pro-v1:0 | 104/120 | B | 0/5 | 11.1s | 39816 |
| lex-bot-deployer | amazon.nova-pro-v1:0 | 100/120 | B | 3/5 | 34.3s | 54765 |
| license-manager-deployer | amazon.nova-pro-v1:0 | 103/120 | B | 4/5 | 9.5s | 39964 |
| lightsail-container-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 11.9s | 44501 |
| lightsail-instance-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 0/5 | 15.6s | 52226 |
| log-retention-automator | amazon.nova-pro-v1:0 | 110/120 | A | 2/5 | 12.7s | 44265 |
| macie-cost-optimizer | amazon.nova-pro-v1:0 | 100/120 | B | 1/5 | 13.0s | 50677 |
| macie-data-classification-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 17.6s | 36862 |
| macie-data-discovery-operator | amazon.nova-pro-v1:0 | 98/120 | B | 4/5 | 18.5s | 34932 |
| managed-blockchain-deployer | amazon.nova-pro-v1:0 | 107/120 | B | 5/5 | 10.9s | 44724 |
| memorydb-cluster-deployer | amazon.nova-pro-v1:0 | 107/120 | B | 3/5 | 14.6s | 48527 |
| migration-hub-strategy-deployer | amazon.nova-pro-v1:0 | 99/120 | B | 0/5 | 5.5s | 45383 |
| msk-cluster-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 12.2s | 36499 |
| msk-cost-optimizer | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 28.8s | 51319 |
| multi-account-governance-automator | amazon.nova-pro-v1:0 | 101/120 | B | 0/5 | 14.4s | 42424 |
| mwaa-environment-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 5.5s | 43806 |
| nat-gateway-cost-optimizer | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 10.6s | 45090 |
| nat-gateway-traffic-optimizer | amazon.nova-pro-v1:0 | 110/120 | A | 5/5 | 9.7s | 54056 |
| neptune-db-cluster-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 3/5 | 15.7s | 46048 |
| neptune-graph-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 0/0 | 10.5s | 42305 |
| network-firewall-rule-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 11.8s | 44421 |
| networkmanager-core-network-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 11.3s | 34956 |
| opensearch-alerting-deployer | amazon.nova-pro-v1:0 | 105/120 | B | 5/5 | 10.5s | 37777 |
| opensearch-cluster-troubleshooter | amazon.nova-pro-v1:0 | 110/120 | A | 0/5 | 14.7s | 46438 |
| opensearch-domain-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 7.9s | 34037 |
| opensearch-domain-deployer | amazon.nova-pro-v1:0 | 100/120 | B | 2/5 | 5.9s | 40080 |
| opensearch-index-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 6.9s | 43240 |
| opensearch-migration-operator | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 16.5s | 43541 |
| opensearch-serverless-deployer | amazon.nova-pro-v1:0 | 104/120 | B | 0/5 | 24.9s | 36838 |
| opensearch-snapshot-troubleshooter | amazon.nova-pro-v1:0 | 111/120 | A | 0/5 | 32.5s | 48362 |
| organizations-account-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 3/5 | 4.8s | 48350 |
| organizations-policy-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 3/5 | 8.7s | 45904 |
| organizations-scp-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 12.7s | 33467 |
| personalize-campaign-deployer | amazon.nova-pro-v1:0 | 100/120 | B | 2/5 | 8.5s | 38991 |
| pinpoint-campaign-deployer | amazon.nova-pro-v1:0 | 105/120 | B | 0/5 | 21.7s | 38322 |
| pinpoint-journey-deployer | amazon.nova-pro-v1:0 | 104/120 | B | 1/5 | 15.4s | 45659 |
| polly-voice-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 4/5 | 9.4s | 44798 |
| qldb-ledger-deployer | amazon.nova-pro-v1:0 | 102/120 | B | 1/5 | 4.9s | 40024 |
| quicksight-dashboard-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 7.0s | 51718 |
| ram-resource-share-deployer | amazon.nova-pro-v1:0 | 98/120 | B | 4/5 | 7.0s | 36660 |
| rds-backup-restore-operator | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 13.0s | 43520 |
| rds-bluegreen-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 8.0s | 44405 |
| rds-connectivity-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 14.1s | 65605 |
| rds-cost-optimizer | amazon.nova-pro-v1:0 | 100/120 | B | 4/5 | 12.4s | 40407 |
| rds-failover-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 0/5 | 15.4s | 52582 |
| rds-instance-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 10.9s | 46275 |
| rds-instance-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 18.6s | 55159 |
| rds-parameter-group-deployer | amazon.nova-pro-v1:0 | 96/120 | B | 5/5 | 21.0s | 41595 |
| rds-proxy-deployer | amazon.nova-pro-v1:0 | 111/120 | A | 3/5 | 16.9s | 38769 |
| rds-snapshot-operator | amazon.nova-pro-v1:0 | 105/120 | B | 5/5 | 17.5s | 50870 |
| rds-upgrade-operator | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 14.3s | 48941 |
| redshift-cluster-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 9.8s | 45953 |
| redshift-cluster-optimizer | amazon.nova-pro-v1:0 | 106/120 | B | 5/5 | 11.8s | 53297 |
| redshift-data-api-deployer | amazon.nova-pro-v1:0 | 103/120 | B | 3/5 | 13.4s | 45712 |
| redshift-query-troubleshooter | amazon.nova-pro-v1:0 | 105/120 | B | 5/5 | 8.8s | 54191 |
| redshift-serverless-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 3/5 | 6.9s | 39786 |
| redshift-wlm-optimizer | amazon.nova-pro-v1:0 | 103/120 | B | 5/5 | 18.1s | 47901 |
| rekognition-collection-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 4/5 | 12.6s | 39194 |
| resiliencehub-app-assessment-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 17.7s | 48588 |
| rolesanywhere-trust-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 2/5 | 10.0s | 47513 |
| route53-application-recovery-controller-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 4/5 | 9.1s | 49132 |
| route53-cost-optimizer | amazon.nova-pro-v1:0 | 101/120 | B | 4/5 | 17.7s | 45509 |
| route53-dns-troubleshooter | amazon.nova-pro-v1:0 | 112/120 | A | 0/5 | 9.4s | 61754 |
| route53-failover-operator | amazon.nova-pro-v1:0 | 109/120 | A | 3/5 | 10.8s | 56613 |
| route53-health-check-troubleshooter | amazon.nova-pro-v1:0 | 102/120 | B | 0/5 | 4.8s | 43316 |
| route53-record-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 9.8s | 37358 |
| route53-resolver-deployer | amazon.nova-pro-v1:0 | 105/120 | B | 4/5 | 22.5s | 44722 |
| route53-routing-policy-deployer | amazon.nova-pro-v1:0 | 102/120 | B | 4/5 | 20.4s | 44733 |
| s3-access-denied-troubleshooter | amazon.nova-pro-v1:0 | 104/120 | B | 0/5 | 11.8s | 53084 |
| s3-access-points-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 17.0s | 49324 |
| s3-access-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 12.0s | 54581 |
| s3-batch-operations-operator | amazon.nova-pro-v1:0 | 109/120 | A | 3/5 | 19.1s | 50324 |
| s3-bucket-policy-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 12.2s | 41226 |
| s3-directory-bucket-deployer | amazon.nova-pro-v1:0 | 105/120 | B | 0/5 | 20.3s | 42934 |
| s3-glacier-restore-operator | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 15.2s | 39528 |
| s3-intelligent-tiering-optimizer | amazon.nova-pro-v1:0 | 106/120 | B | 5/5 | 40.4s | 48632 |
| s3-lifecycle-automator | amazon.nova-pro-v1:0 | 101/120 | B | 2/5 | 14.9s | 38387 |
| s3-lifecycle-optimizer | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 18.2s | 74901 |
| s3-object-lambda-deployer | amazon.nova-pro-v1:0 | 105/120 | B | 0/5 | 15.5s | 47978 |
| s3-outposts-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 11.2s | 41817 |
| s3-performance-optimizer | amazon.nova-pro-v1:0 | 103/120 | B | 5/5 | 6.2s | 40383 |
| s3-public-access-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 14.7s | 40044 |
| s3-replication-operator | amazon.nova-pro-v1:0 | 111/120 | A | 3/5 | 10.9s | 51978 |
| s3-secure-bucket-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 3/5 | 17.3s | 50179 |
| s3-storage-class-optimizer | amazon.nova-pro-v1:0 | 110/120 | A | 5/5 | 8.0s | 48754 |
| s3-table-bucket-deployer | amazon.nova-pro-v1:0 | 104/120 | B | 4/5 | 25.4s | 47706 |
| s3-transfer-acceleration-operator | amazon.nova-pro-v1:0 | 101/120 | B | 2/5 | 10.2s | 42208 |
| s3-version-cleanup-operator | amazon.nova-pro-v1:0 | 102/120 | B | 5/5 | 7.9s | 41351 |
| sagemaker-endpoint-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 5.5s | 37189 |
| sagemaker-endpoint-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 13.9s | 48783 |
| sagemaker-model-registry-operator | amazon.nova-pro-v1:0 | 106/120 | B | 2/5 | 14.8s | 44932 |
| sagemaker-pipeline-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 3/5 | 9.8s | 43740 |
| sagemaker-training-job-operator | amazon.nova-pro-v1:0 | 111/120 | A | 3/5 | 27.7s | 48941 |
| secrets-manager-rotation-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 16.7s | 68424 |
| secrets-rotation-operator | amazon.nova-pro-v1:0 | 112/120 | A | 3/5 | 13.4s | 47093 |
| secretsmanager-rotation-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 11.2s | 48554 |
| securityhub-control-compliance-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 11.6s | 47500 |
| securityhub-finding-troubleshooter | amazon.nova-pro-v1:0 | 106/120 | B | 0/5 | 25.5s | 42947 |
| securityhub-remediation-automator | amazon.nova-pro-v1:0 | 106/120 | B | 0/5 | 11.9s | 45258 |
| serverlessrepo-application-deployer | amazon.nova-pro-v1:0 | 103/120 | B | 2/5 | 10.0s | 42888 |
| service-catalog-portfolio-deployer | amazon.nova-pro-v1:0 | 103/120 | B | 3/5 | 15.3s | 41210 |
| service-quotas-usage-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 5.6s | 36547 |
| ses-email-deployer | amazon.nova-pro-v1:0 | 97/120 | B | 4/5 | 6.0s | 44283 |
| shield-advanced-coverage-auditor | amazon.nova-pro-v1:0 | 116/120 | A | 6/6 | 4.5s | 46206 |
| signer-signing-profile-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 3/5 | 12.8s | 49036 |
| sitewise-asset-deployer | amazon.nova-pro-v1:0 | 110/120 | A | 4/5 | 7.0s | 53574 |
| snowball-edge-deployer | amazon.nova-pro-v1:0 | 110/120 | A | 5/5 | 16.1s | 42646 |
| sns-delivery-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 12.2s | 45110 |
| sns-subscription-operator | amazon.nova-pro-v1:0 | 110/120 | A | 4/5 | 8.8s | 45981 |
| sns-topic-deployer | amazon.nova-pro-v1:0 | 100/120 | B | 2/5 | 11.9s | 40062 |
| sns-topic-public-subscription-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 17.2s | 39910 |
| sqs-dead-letter-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 17.4s | 62996 |
| sqs-dlq-operator | amazon.nova-pro-v1:0 | 104/120 | B | 3/5 | 12.3s | 45481 |
| sqs-dlq-policy-auditor | amazon.nova-pro-v1:0 | 112/120 | A | 6/6 | 13.2s | 39513 |
| sqs-fifo-deployer | amazon.nova-pro-v1:0 | 103/120 | B | 3/5 | 7.6s | 43178 |
| sqs-queue-deployer | amazon.nova-pro-v1:0 | 110/120 | A | 4/5 | 18.4s | 41800 |
| sqs-throughput-optimizer | amazon.nova-pro-v1:0 | 104/120 | B | 5/5 | 6.1s | 51887 |
| ssm-association-operator | amazon.nova-pro-v1:0 | 97/120 | B | 4/5 | 9.4s | 39935 |
| ssm-association-troubleshooter | amazon.nova-pro-v1:0 | 104/120 | B | 5/5 | 14.8s | 39798 |
| ssm-automation-deployer | amazon.nova-pro-v1:0 | 99/120 | B | 4/5 | 8.0s | 41502 |
| ssm-managed-instance-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 30.7s | 46060 |
| ssm-patch-baseline-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 13.9s | 45209 |
| ssm-patch-compliance-automator | amazon.nova-pro-v1:0 | 103/120 | B | 0/5 | 7.2s | 38617 |
| ssm-patch-operator | amazon.nova-pro-v1:0 | 111/120 | A | 5/5 | 15.2s | 48540 |
| ssm-session-manager-troubleshooter | amazon.nova-pro-v1:0 | 101/120 | B | 5/5 | 12.3s | 51910 |
| ssm-session-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 0/5 | 15.5s | 47380 |
| stepfunctions-execution-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 10.4s | 51195 |
| stepfunctions-express-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 3/5 | 13.9s | 52383 |
| stepfunctions-map-state-deployer | amazon.nova-pro-v1:0 | 103/120 | B | 4/5 | 25.4s | 43914 |
| stepfunctions-statemachine-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 16.3s | 46991 |
| stepfunctions-statemachine-deployer | amazon.nova-pro-v1:0 | 115/120 | A | 3/5 | 19.4s | 63461 |
| storage-gateway-deployer | amazon.nova-pro-v1:0 | 102/120 | B | 5/5 | 12.3s | 47402 |
| sts-cross-account-role-auditor | amazon.nova-pro-v1:0 | 114/120 | A | 6/6 | 9.3s | 47639 |
| tag-compliance-automator | amazon.nova-pro-v1:0 | 107/120 | B | 0/5 | 12.1s | 44410 |
| tag-governance-automator | amazon.nova-pro-v1:0 | 109/120 | A | 2/5 | 16.5s | 54948 |
| textract-document-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 9.1s | 44119 |
| timestream-database-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 16.0s | 50793 |
| transcribe-job-deployer | amazon.nova-pro-v1:0 | 111/120 | A | 4/5 | 17.3s | 42407 |
| transfer-cost-optimizer | amazon.nova-pro-v1:0 | 106/120 | B | 4/5 | 15.6s | 50037 |
| transfer-family-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 4/5 | 25.8s | 47646 |
| transfer-family-workflow-deployer | amazon.nova-pro-v1:0 | 100/120 | B | 3/5 | 23.1s | 43230 |
| transit-gateway-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 2/5 | 7.7s | 61202 |
| transit-gateway-routing-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 13.7s | 46176 |
| trustedadvisor-check-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 16.1s | 40241 |
| verified-permissions-policy-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 10.6s | 40262 |
| vpc-connectivity-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 39.9s | 71520 |
| vpc-endpoint-policy-troubleshooter | amazon.nova-pro-v1:0 | 105/120 | B | 5/5 | 7.3s | 44763 |
| vpc-lattice-auth-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 8.7s | 40248 |
| vpc-network-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 14.4s | 62426 |
| vpc-peering-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 11.3s | 46939 |
| vpclattice-service-deployer | amazon.nova-pro-v1:0 | 107/120 | B | 4/5 | 6.0s | 47186 |
| vpn-connection-deployer | amazon.nova-pro-v1:0 | 109/120 | A | 0/0 | 10.4s | 43500 |
| waf-rule-deployer | amazon.nova-pro-v1:0 | 101/120 | B | 3/5 | 16.7s | 48258 |
| wafv2-web-acl-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 12.1s | 43695 |
| wafv2-web-acl-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 12.1s | 43711 |
| wellarchitected-review-operator | amazon.nova-pro-v1:0 | 101/120 | B | 3/5 | 9.8s | 49000 |
| wellarchitected-workload-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 20.5s | 41739 |
| xray-tracing-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 19.3s | 40611 |
<!-- END EVAL SCORECARD TABLE -->

> Scorecard rows appear once eval runs commit JSON artifacts to `eval/scorecards/`. Run `python3 eval/generate_readme_table.py` to refresh.

**Eval-backed standard: ALL 79 audit skills are Grade A (>=108/120)** -- zero exceptions. Every audit skill is measured by the median-of-3 judge (reproducible); none assert quality without evidence. Non-audit skills (deploy/troubleshoot/optimize/operate) carry assertion-layer evals; median-of-3 judge scorecards pending.

---

## Eval pipeline

```text
skills/*/eval/test-cases.yaml  ->  eval/run_eval.py
                                  ->  aws bedrock-runtime converse  (Nova Pro target)
                                  ->  assertion layer  (must_contain / must_not_contain)
                                  ->  LLM judge  (gpt-oss-120b, 8-dim rubric, median-of-3)
                                  ->  JSON scorecard  (committed artifact)
```

- **Target models:** Amazon Nova Pro (`amazon.nova-pro-v1:0`) and `openai.gpt-oss-20b`.
- **Judge:** `openai.gpt-oss-120b-1:0` via the [softaworks skill-judge](https://github.com/softaworks/agent-toolkit/tree/main/skills/skill-judge) 8-dimension / 120-point rubric. The **median of 3 runs** gives stable, reproducible scores.
- **CI:** assertion-only on every PR (no AWS credentials). The maintainer runs the LLM-judge locally and commits scorecard artifacts.
- **Grade floor:** Grade A (>=108/120). Every shipped skill clears this.

### Eval structure (per skill)

Each skill has TWO eval surfaces:

| Directory | Purpose | Contents |
|---|---|---|
| `eval/` | **Assertion layer** (CI-runnable, deterministic, no AWS creds) | `test-cases.yaml` -- objective test cases with `must_contain` / `must_not_contain` verdict tokens |
| `evals/` | **Structured eval surface** (the full eval definition) | `evals.json` (case metadata + difficulty + assertions), `prompts/` (the eval prompts sent to the model), `baselines/` (the **without-skill** baseline response -- proving the skill adds value via the delta) |

The `evals/` structure follows the [OpenAI eval-skills guidance](https://developers.openai.com/blog/eval-skills) and [Anthropic's "Demystifying evals for AI agents"](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) -- structured eval cases, baselines for the with-skill-vs-without-skill **delta comparison**, and per-case difficulty/metadata. The `eval/` assertion layer is the CI-runnable subset (deterministic verdict checks on every PR without AWS credentials).

### Run the eval yourself

```bash
# Assertion layer only (no AWS credentials needed)
python3 eval/run_eval.py --assertion-only

# Full eval (target model + LLM judge) -- requires AWS SSO
aws sso login --profile default
python3 eval/run_eval.py                 # all skills
python3 eval/run_eval.py --skill s3-public-access-auditor  # one skill

# Impact eval (with-skill vs without-skill delta) -- requires AWS SSO
python3 eval/impact_eval.py --skill s3-public-access-auditor
```

---

## FAQ

### Why not ride on `aws/agent-toolkit-for-aws`?

We investigated this thoroughly. `aws/agent-toolkit-for-aws` (the official AWS repo, 140 skills, 2,200+ stars) has a **dual block on external contributions**:

1. `CONTRIBUTING.md` states verbatim: *"This project is not accepting external code contributions at this time."*
2. GitHub enforces `pull_request_creation_policy: collaborators_only` -- public forks **cannot even open PRs**.

Of the last 100 PRs, 97 are from AWS staff; there is **no documented pathway** for a new external contributor to get collaborator status. We cannot contribute to it.

The adjacent `awslabs/agent-plugins` (848 stars) **does** accept external PRs (7+ merged from external authors in 60 days) -- and we keep that door open as a **future amplification path** (contribute the best-of Grade-A auditors upstream once organic reach demands it). But for now, the independent repo is the fastest path to shipping eval-backed skills.

**The real wedge:** this repo ships **committed eval scorecards** (median-of-3 judge, Grade A) -- zero existing AWS skill repo does. That is the differentiator: *measured, not vibes.*

### How does the eval actually work?

1. **Nova Pro** executes the skill (runs the audit on the test-case input).
2. An **assertion layer** checks the model output for required verdict tokens (deterministic, CI-runnable).
3. **gpt-oss-120b** judges the skill definition against the softaworks 8-dimension rubric (adversarial, default-deduct, per-dimension justification).
4. The **median of 3 judge runs** gives a stable score (the judge has +/-5 run-to-run variance; the median removes it).
5. The result is a committed JSON scorecard + a Grade (A/B/C/D/F).

### What models does this repo use?

- **Target** (executes the skill): Amazon Nova Pro, gpt-oss-20b.
- **Judge** (scores the skill): gpt-oss-120b.


### What does Grade A mean?

>=108/120 (90%) on the softaworks 8-dimension rubric. Every shipped skill clears this floor.

### How do I contribute a skill?

1. Create `skills/<your-skill>/SKILL.md` (follow `schema/SKILL.schema.json`).
2. Add `eval/test-cases.yaml` with 5-6 objective, deterministic test cases.
3. Run `python3 eval/run_eval.py --skill <your-skill>` and confirm Grade A.
4. Run `python3 eval/generate_readme_table.py` to update the README.
5. Open a PR. CI runs the assertion layer; the maintainer reviews + commits the judge scorecard.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full structured-eval pattern.

### How is this different from `itsmostafa/aws-agent-skills`?

`itsmostafa/aws-agent-skills` (18 skills) ships **service-overview docs** (what a service *is*) with **zero evals**. This repo ships **detective auditors** (what to *check* + the measured eval proving the check works). Different artifact, different quality bar.

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full guide on adding a skill (the directory structure, the eval contract, the schema, and the slash-command pattern).

Every contribution must ship with:
- `SKILL.md` (schema-valid frontmatter + the audit classification logic)
- `eval/test-cases.yaml` (5-6 deterministic test cases with concept-token assertions)
- A committed scorecard at Grade A

---

## Coverage

**90 eval-backed skills across 12 CloudOps families and 5 task types** (79 audit + 4 deploy + 3 troubleshoot + 2 optimize + 1 operate + 1 orchestrator):

| Task type | Count | What it does |
|---|---|---|
| **audit** | 80 | Assess security posture, compliance, configuration drift |
| **deploy** | 4 | Provision infrastructure with correct defaults |
| **troubleshoot** | 3 | Diagnose and resolve operational issues |
| **optimize** | 2 | Reduce cost / improve performance |
| **operate** | 1 | Day-2 operations (backup, restore, failover) |

| Family | Count | Examples |
|---|---|---|
| Security | 23 | S3, IAM, EC2, GuardDuty, KMS, WAFv2, Secrets Manager, Inspector2, ACM, STS, Cognito, Access Analyzer, Security Hub, Macie, Firewall Manager, Detective, Shield, Network Firewall, Verified Permissions, VPC Lattice, CloudHSM, **IAM Role Deployer**, **IAM Permission Troubleshooter** |
| Compute | 7 | Lambda, ECS, ECR, EKS, Auto Scaling, Compute Optimizer, **Lambda Deployer** |
| Storage | 5 | EBS, EFS, Backup, DLM, **S3 Secure Bucket Deployer**, **S3 Lifecycle Optimizer** |
| Networking | 6 | CloudFront, ELBv2, Route53, DirectConnect, Network Manager, **VPC Network Deployer** |
| FinOps | 5 | Billing, Budgets, Cost Explorer, Cost Optimization Hub, CUR |
| Governance | 7 | CloudTrail, Config, Organizations, Control Tower, Well-Architected, Trusted Advisor, Audit Manager |
| Databases | 4 | RDS, DynamoDB, **RDS Connectivity Troubleshooter**, **RDS Backup Restore Operator** |
| App Integration | 5 | SQS, SNS, EventBridge, Step Functions, API Gateway |
| Developer Tools | 4 | CodeBuild, CodeCommit, CodeDeploy, CodePipeline |
| AI/ML | 3 | Bedrock Guardrails, Bedrock Model Access, SageMaker |
| Management | 7 | CloudWatch Alarms, CloudWatch Logs, SSM, Service Quotas, Health, Resilience Hub, **EC2 Rightsizing Optimizer** |
| Analytics | 10 | Athena, Glue, Kinesis, OpenSearch, LakeFormation, Redshift, Firehose, MSK, EMR, CleanRooms |
| Migration | 1 | DMS |

### Skill universe — the full roadmap

The complete enumeration of planned skills is in [`features/aws-cloudops-skills-oss/skill-universe.md`](./features/aws-cloudops-skills-oss/skill-universe.md) — every CloudOps-relevant AWS service × every applicable task type (~500 total skill slots, 90 built today). The universe grows through phased builds toward exhaustive coverage.

### Skill lifecycle — capability vs preference + retirement

Every skill is classified as:
- **capability** — durable knowledge the model fundamentally lacks (AWS-specific diagnostic procedures, config rules, gotchas). Survives model improvements.
- **preference** — temporary workflow/style guidance the model will internalize over time. Retired when the model's without-skill performance matches with-skill.

The **impact eval** (`eval/impact_eval.py`) measures the with-skill vs without-skill performance delta. Skills where the delta ≤ 0 are tagged RETIRE_CANDIDATE. See [MAINTENANCE.md](./MAINTENANCE.md) for the quarterly retirement cadence.

---

## License

[Apache License 2.0](./LICENSE) -- See [NOTICE](./NOTICE) for AWS trademark attribution.

## Author

**Jacky Chan** -- AWS Community Builder (ML & GenAI). Personal project, not affiliated with any employer.
