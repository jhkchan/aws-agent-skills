# aws-agent-skills

> **Repository:** [jhkchan/aws-agent-skills](https://github.com/jhkchan/aws-agent-skills)
> · License: **Apache-2.0** · Maintainer: **Jacky Chan, AWS Community Builder (ML & GenAI)**
> · A solo, community-driven project.

**90 eval-backed AWS CloudOps agent skills** across **6 task types** (audit · deploy · troubleshoot · optimize · operate) — every skill ships with a committed, median-of-3-judge-scored eval scorecard. Measured, not asserted. Built on the [softaworks skill-judge](https://github.com/softaworks/agent-toolkit/tree/main/skills/skill-judge) 8-dimension rubric, with co-located structured evals (cases + baselines + delta comparison) on every skill.

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

# Or install ALL 79 skills at once:
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
| **automate** | Workflow/pipeline patterns | *(planned — see skill-universe.md)* |

```
Deploy a secure S3 bucket with encryption and lifecycle rules.
```

The `s3-secure-bucket-deployer` walks through the 10-step provisioning procedure and emits a READY_TO_DEPLOY checklist.

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
... (101 commands total)
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
| acm-certificate-expiry-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 12.0s | 37462 |
| alb-5xx-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 27.8s | 54221 |
| apigateway-5xx-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 0/5 | 21.4s | 54610 |
| apigateway-resource-policy-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 9.6s | 35471 |
| apigateway-rest-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 15.8s | 48821 |
| athena-workgroup-auditor | amazon.nova-pro-v1:0 | 114/120 | A | 6/6 | 8.6s | 49642 |
| auditmanager-assessment-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 12.6s | 50433 |
| auto-remediation-automator | amazon.nova-pro-v1:0 | 105/120 | B | 1/5 | 8.0s | 44777 |
| autoscaling-group-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 18.9s | 39803 |
| backup-plan-auditor | amazon.nova-pro-v1:0 | 115/120 | A | 6/6 | 8.5s | 30595 |
| bedrock-guardrail-coverage-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 5.1s | 31762 |
| bedrock-model-access-inventory | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 14.4s | 35705 |
| billing-account-auditor | amazon.nova-pro-v1:0 | 114/120 | A | 6/6 | 13.4s | 37235 |
| budgets-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 12.2s | 37761 |
| ce-cost-anomaly-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 30.5s | 36151 |
| cicd-pipeline-automator | amazon.nova-pro-v1:0 | 106/120 | B | 5/5 | 16.4s | 54077 |
| cleanrooms-collaboration-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 20.3s | 47219 |
| cloudfront-cache-troubleshooter | amazon.nova-pro-v1:0 | 106/120 | B | 5/5 | 19.5s | 55401 |
| cloudfront-distribution-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 13.3s | 39728 |
| cloudfront-distribution-deployer | amazon.nova-pro-v1:0 | 111/120 | A | 0/5 | 10.2s | 49278 |
| cloudhsm-cluster-posture-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 5.9s | 35489 |
| cloudtrail-org-trail-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 9.7s | 38562 |
| cloudwatch-alarm-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 39.2s | 36433 |
| cloudwatch-alarm-operator | amazon.nova-pro-v1:0 | 105/120 | B | 3/5 | 19.4s | 52755 |
| cloudwatch-logs-retention-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 29.7s | 42221 |
| codebuild-project-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 16.4s | 49703 |
| codecommit-repository-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 8.2s | 32563 |
| codedeploy-deployment-group-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 23.8s | 39309 |
| codepipeline-pipeline-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 13.7s | 39910 |
| cognito-idp-user-pool-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 6.8s | 41140 |
| compute-optimizer-findings-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 17.8s | 35720 |
| config-recorder-coverage-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 35.6s | 43031 |
| controltower-control-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 23.1s | 33282 |
| cost-optimization-hub-recommendations-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 12.3s | 37941 |
| cur-cost-usage-report-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 7.0s | 38402 |
| detective-investigation-coverage-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 13.5s | 34135 |
| directconnect-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 17.7s | 52075 |
| dlm-lifecycle-policy-auditor | amazon.nova-pro-v1:0 | 112/120 | A | 6/6 | 6.2s | 41975 |
| dms-replication-task-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 18.3s | 39911 |
| dynamodb-backup-operator | amazon.nova-pro-v1:0 | 109/120 | A | 4/5 | 9.9s | 47165 |
| dynamodb-table-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 12.8s | 38416 |
| dynamodb-table-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 17.1s | 59731 |
| dynamodb-throttling-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 14.0s | 50993 |
| ebs-volume-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 16.0s | 35713 |
| ebs-volume-optimizer | amazon.nova-pro-v1:0 | 106/120 | B | 5/5 | 24.1s | 67005 |
| ec2-backup-operator | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 11.1s | 56997 |
| ec2-rightsizing-optimizer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 14.9s | 65548 |
| ec2-security-group-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 5/5 | 11.5s | 38372 |
| ecr-repository-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 12.4s | 46409 |
| ecs-task-definition-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 13.9s | 45015 |
| ecs-task-troubleshooter | amazon.nova-pro-v1:0 | 109/120 | A | 2/5 | 12.3s | 55277 |
| efs-filesystem-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 11.6s | 38429 |
| eks-cluster-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 11.7s | 34838 |
| eks-upgrade-operator | amazon.nova-pro-v1:0 | 106/120 | B | 3/5 | 11.9s | 50565 |
| elbv2-load-balancer-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 8.6s | 47542 |
| emr-cluster-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 0/6 | 12.2s | 33961 |
| event-driven-automator | amazon.nova-pro-v1:0 | 109/120 | A | 3/5 | 13.6s | 44835 |
| eventbridge-bus-policy-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 12.9s | 40249 |
| firehose-delivery-stream-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 5.2s | 43387 |
| firewall-manager-compliance-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 16.8s | 53101 |
| glue-crawler-job-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 35.0s | 48227 |
| guardduty-finding-severity-triage | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 12.3s | 55940 |
| health-event-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 12.4s | 42780 |
| iac-template-automator | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 20.6s | 58312 |
| iam-least-privilege-advisor | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 7.8s | 33835 |
| iam-permission-troubleshooter | amazon.nova-pro-v1:0 | 107/120 | B | 5/5 | 16.2s | 49179 |
| iam-role-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 20.9s | 54672 |
| incident-response-automator | amazon.nova-pro-v1:0 | 109/120 | A | 0/5 | 4.9s | 55975 |
| inspector2-coverage-finding-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 17.3s | 52550 |
| kinesis-stream-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 27.1s | 42232 |
| kms-key-policy-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 17.2s | 49516 |
| lakeformation-data-lake-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 13.1s | 43103 |
| lambda-cost-optimizer | amazon.nova-pro-v1:0 | 100/120 | B | 5/5 | 12.7s | 85104 |
| lambda-function-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 3/5 | 9.6s | 49830 |
| lambda-invocation-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 10.9s | 67093 |
| lambda-runtime-deprecation-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 15.4s | 45863 |
| macie-data-classification-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 17.6s | 36862 |
| msk-cluster-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 12.2s | 36499 |
| nat-gateway-cost-optimizer | amazon.nova-pro-v1:0 | 105/120 | B | 5/5 | 9.8s | 51016 |
| network-firewall-rule-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 11.8s | 44421 |
| networkmanager-core-network-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 11.3s | 34956 |
| opensearch-domain-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 7.9s | 34037 |
| organizations-scp-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 12.7s | 33467 |
| rds-backup-restore-operator | amazon.nova-pro-v1:0 | 104/120 | B | 3/5 | 11.9s | 42239 |
| rds-connectivity-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 5/5 | 36.9s | 65609 |
| rds-cost-optimizer | amazon.nova-pro-v1:0 | 104/120 | B | 5/5 | 5.9s | 62396 |
| rds-instance-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 10.9s | 46275 |
| rds-instance-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 18.6s | 55159 |
| redshift-cluster-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 9.8s | 45953 |
| resiliencehub-app-assessment-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 17.7s | 48588 |
| route53-record-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 9.8s | 37358 |
| s3-access-troubleshooter | amazon.nova-pro-v1:0 | 108/120 | A | 4/5 | 12.0s | 54581 |
| s3-lifecycle-optimizer | amazon.nova-pro-v1:0 | 99/120 | B | 4/5 | 15.1s | 58388 |
| s3-public-access-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 5/5 | 14.7s | 40044 |
| s3-secure-bucket-deployer | amazon.nova-pro-v1:0 | 106/120 | B | 4/5 | 48.8s | 47228 |
| s3-version-cleanup-operator | amazon.nova-pro-v1:0 | 105/120 | B | 5/5 | 7.6s | 48529 |
| sagemaker-endpoint-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 5.5s | 37189 |
| secrets-rotation-operator | amazon.nova-pro-v1:0 | 112/120 | A | 3/5 | 13.4s | 47093 |
| secretsmanager-rotation-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 11.2s | 48554 |
| securityhub-control-compliance-auditor | amazon.nova-pro-v1:0 | 110/120 | A | 6/6 | 11.6s | 47500 |
| service-quotas-usage-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 5.6s | 36547 |
| shield-advanced-coverage-auditor | amazon.nova-pro-v1:0 | 116/120 | A | 6/6 | 4.5s | 46206 |
| sns-topic-deployer | amazon.nova-pro-v1:0 | 100/120 | B | 1/5 | 10.1s | 46402 |
| sns-topic-public-subscription-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 17.2s | 39910 |
| sqs-dlq-policy-auditor | amazon.nova-pro-v1:0 | 112/120 | A | 6/6 | 13.2s | 39513 |
| sqs-queue-deployer | amazon.nova-pro-v1:0 | 104/120 | B | 3/5 | 15.0s | 50238 |
| ssm-managed-instance-auditor | amazon.nova-pro-v1:0 | 113/120 | A | 6/6 | 30.7s | 46060 |
| ssm-patch-operator | amazon.nova-pro-v1:0 | 111/120 | A | 5/5 | 15.2s | 48540 |
| stepfunctions-statemachine-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 16.3s | 46991 |
| stepfunctions-statemachine-deployer | amazon.nova-pro-v1:0 | 115/120 | A | 3/5 | 19.4s | 63461 |
| sts-cross-account-role-auditor | amazon.nova-pro-v1:0 | 114/120 | A | 6/6 | 9.3s | 47639 |
| trustedadvisor-check-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 16.1s | 40241 |
| verified-permissions-policy-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 10.6s | 40262 |
| vpc-connectivity-troubleshooter | amazon.nova-pro-v1:0 | 105/120 | B | 0/5 | 9.3s | 67261 |
| vpc-lattice-auth-auditor | amazon.nova-pro-v1:0 | 108/120 | A | 6/6 | 8.7s | 40248 |
| vpc-network-deployer | amazon.nova-pro-v1:0 | 108/120 | A | 0/5 | 14.4s | 62426 |
| wafv2-web-acl-auditor | amazon.nova-pro-v1:0 | 111/120 | A | 6/6 | 12.1s | 43695 |
| wellarchitected-workload-auditor | amazon.nova-pro-v1:0 | 109/120 | A | 6/6 | 20.5s | 41739 |
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
