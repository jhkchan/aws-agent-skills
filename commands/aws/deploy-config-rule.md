---
description: Provision AWS Config rules with production-grade compliance coverage (managed rules, custom Lambda rules, conformance packs, organization rules, proactive rules). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create config rule"
  - "deploy config rule"
  - "managed config rule"
  - "custom config rule"
  - "lambda config rule"
  - "conformance pack"
  - "organization config rule"
  - "org config rule"
  - "config remediation"
  - "ssm automation remediation"
  - "security hub config"
  - "configuration recorder"
  - "delivery channel"
  - "proactive config rule"
  - "cloudformation hook config"
  - "cis benchmark config"
  - "pci-dss config rules"
  - "tagging enforcement rule"
  - "config compliance"
  - "put-config-rule"
  - "aws config governance"
routes_to: config-rule-deployer
---

# /aws:deploy-config-rule

Activate the `config-rule-deployer` skill and provision AWS Config
rules with production-grade compliance coverage and remediation wiring.

## What it does

The skill walks a pre-check gate and emits a READY_TO_DEPLOY checklist:

1. Configuration recorder status verification (recording = true)
2. Delivery channel verification (S3 bucket exists)
3. Managed rule identifier validation
4. Custom Lambda function existence + Config invocation permission
5. Resource scope validation (supported resource types)
6. Evaluation mode selection (configuration-change vs periodic)
7. SSM Automation remediation document verification
8. Conformance pack template validation
9. Organization config rule authorization check
10. Proactive rule (CloudFormation hook) registration

## When to use

- You need to create a new Config rule (managed, custom, or org-wide).
- You are deploying a compliance baseline (CIS, PCI-DSS, NIST).
- You need to wire SSM Automation remediation to a Config rule.
- You want to deploy conformance packs across your organization.
- You need to set up the configuration recorder and delivery channel.
- You want to deploy proactive rules to block non-compliant resources.
- You need copy-pasteable put-config-rule commands.

## How to invoke

### Slash command

```
/aws:deploy-config-rule
```

Then provide: rule name, rule type (managed / custom / conformance-pack /
org / proactive), managed rule identifier or Lambda function ARN, resource
scope, evaluation mode, remediation configuration, and target region.

### Natural language

Any of these routes to the same skill:

- "create a Config rule for S3 public read prevention"
- "deploy a CIS benchmark conformance pack"
- "set up a custom Lambda Config rule for tagging"
- "configure SSM Automation remediation"
- "deploy an organization config rule"

### CLI routing

```bash
node cli/bin/cli.js route "create a config rule"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or update
Config rules. The output checklist feeds into verification pipelines
and audit skills (config-rule-compliance-auditor for post-deploy audit).

## Example

```
You: /aws:deploy-config-rule

     Create a managed Config rule s3-bucket-public-read-prohibited
     in us-east-1. Scope to S3 buckets. Add SSM Automation remediation
     with AWS-DisableS3BucketPublicReadWrite, auto-remediate.
     Account: 111111111111.

Skill:
  RULE: s3-bucket-public-read-prohibited
  VERDICT: READY_TO_DEPLOY
  TARGET: s3-bucket-public-read-prohibited
  PRE_CHECKS:
    [PASS] Configuration recorder active (recording = true)
    [PASS] Delivery channel configured (S3 bucket: config-bucket-111111111111)
    [PASS] ManagedRuleIdentifier S3_BUCKET_PUBLIC_READ_PROHIBITED valid
    [PASS] Scope AWS::S3::Bucket is supported
    [PASS] SSM document AWS-DisableS3BucketPublicReadWrite exists
    [PASS] 12 + 1 = 13 rules <= 150 limit
  EVALUATION: configuration-change:1-30min
  REMEDIATION: auto:AWS-DisableS3BucketPublicReadWrite
```

## References

- Skill definition: `skills/config-rule-deployer/SKILL.md`
- Rule catalog reference: `skills/config-rule-deployer/references/config-rule-catalog.md`
- Eval suite: `skills/config-rule-deployer/evals/evals.json`
