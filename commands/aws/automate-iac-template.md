---
description: Generate and validate Infrastructure-as-Code templates for common AWS patterns across CloudFormation, CDK v2, and Terraform. Covers VPC, serverless, ECS Fargate, RDS Aurora, CloudFront+S3+WAF. Enforces least-privilege IAM, encryption-by-default, no hardcoded secrets, drift detection, change-set preview.
nl_triggers:
  - "generate CloudFormation template"
  - "write CDK code for"
  - "Terraform module for AWS"
  - "IaC for VPC with NAT"
  - "serverless template Lambda API Gateway DynamoDB"
  - "ECS Fargate service template"
  - "RDS Aurora with secret rotation IaC"
  - "validate this CloudFormation template"
  - "cfn-lint findings on"
  - "terraform plan shows"
  - "drift detection on stack"
  - "convert manual AWS resources to IaC"
  - "cfn-nag"
  - "tflint"
  - "checkov"
routes_to: iac-template-automator
---

# /aws:automate-iac-template

Activate the `iac-template-automator` skill and produce an IaC template
(or validation report) for a common AWS pattern.

## What it does

Reads a pattern specification (vpc, serverless-lambda-apigw,
ecs-fargate-alb, rds-aurora-secret-rotation, cloudfront-s3-waf, or
custom), a tool selection (cloudformation, cdk, terraform), and either:

1. **Generates** a complete template with the security baseline applied
   (least-privilege IAM, encryption-by-default, deletion protection on
   prod data stores, tags for cost allocation).
2. **Validates** an existing template against the 12-rule security
   baseline + cfn-lint / cfn-nag / tflint / checkov findings.

Emits a deterministic block per template:

```text
PATTERN: <vpc | serverless-lambda-apigw | ecs-fargate-alb | ...>
TOOL: <cloudformation | cdk | terraform>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
TEMPLATE:
  <generated template content or path>
VALIDATION:
  - [PASS|FAIL|WARN] cfn-lint: <findings>
  - [PASS|FAIL|WARN] cfn-nag: <findings>
  - [PASS|FAIL|WARN] tflint: <findings>
  - [PASS|FAIL|WARN] checkov: <findings>
SECURITY:
  - [PASS|FAIL|WARN] <each of the 12 security baseline rules>
FINDINGS:
  - [INFO|WARN|HIGH|CRITICAL] <observation>
REMEDIATION:
  <numbered steps for fixing any FAIL findings>
```

## When to invoke

Provide a pattern + tool and ask any of:

- "generate a CloudFormation template for a serverless app"
- "write CDK code for a VPC with 3 AZs and 2 NAT gateways"
- "Terraform module for an ECS Fargate service behind an ALB"
- "validate this CloudFormation template for security"
- "convert this manual S3 bucket setup to Terraform"
- "why is cfn-nag flagging F3 on my template"

A bare pattern + tool + "generate" routes here via the orchestrator.

## Inputs

- **Required:** pattern (vpc | serverless-lambda-apigw | ecs-fargate-alb
  | rds-aurora-secret-rotation | cloudfront-s3-waf | custom), tool
  (cloudformation | cdk | terraform).
- **Optional:** environment (dev/stage/prod, drives deletion-protection
  and encryption defaults), region, account_id, existing_template (for
  validation mode), capabilities required.

## Outputs

- One VERDICT block per template (AUTOMATED or MANUAL_STEP_REQUIRED).
- The complete generated template content (inline if small, path if
  large) in TEMPLATE.
- Validation findings from cfn-lint, cfn-nag, tflint, checkov in
  VALIDATION.
- Security baseline pass/fail per rule in SECURITY.
- Specific remediation steps for any failing gate in REMEDIATION.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Automate specialist for IaC generation and validation).
- `/aws:deploy-iam-role` for IAM role-specific deployment plans.
- `/aws:deploy-vpc-network` for VPC-specific deployment plans.
- `/aws:audit-cloudtrail-org-trail` for auditing the CloudTrail trail
  that IaC templates typically create.
