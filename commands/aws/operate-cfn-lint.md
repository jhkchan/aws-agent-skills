---
description: Operate CloudFormation template linting and validation (cfn-lint static analysis, validate-template syntax check, cfn-nag security scanning, ChangeSet creation, drift detection, stack policy enforcement, SAM/nested stack validation). Emits an OPERATION_COMPLETED checklist with verification commands.
nl_triggers:
  - "cfn lint"
  - "cloudformation validate"
  - "validate template"
  - "cfn nag"
  - "cfn-nag scan"
  - "changeset create"
  - "drift detection"
  - "stack policy"
  - "sam transform validation"
  - "nested stack validation"
  - "cloudformation lint"
  - "template security scan"
routes_to: cloudformation-cfn-lint-operator
---

# /aws:operate-cfn-lint

Activate the `cloudformation-cfn-lint-operator` skill and run the
four-layer CloudFormation validation pipeline.

## What it does

The skill walks the validation procedure and emits an
OPERATION_COMPLETED checklist:

1. cfn-lint static analysis (structural/logical errors)
2. Pre-deploy validation (validate-template syntax check)
3. ChangeSet creation (exact resource change preview)
4. Drift detection (stack drift status)
5. Stack policy enforcement (resource protection)
6. cfn-nag security scanning (wildcard IAM, unencrypted resources)
7. SAM transform validation (expand then lint)
8. Nested stack validation (each child independently)
9. Resource import validation
10. Macro expansion validation
11. IaC pipeline integration (CodePipeline gates)
12. Rollback template archive

## When to use

- You need to validate a CloudFormation template before deployment.
- You need to create a ChangeSet to preview resource changes.
- You need to scan a template for security anti-patterns (cfn-nag).
- You need to detect stack drift.
- You need to enforce a stack policy.
- You need to validate a SAM template or nested stacks.
- You need to integrate CloudFormation linting into a CI/CD pipeline.

## When NOT to use

- **Terraform validation** — use tflint instead.
- **AWS CDK** — use `cdk synth` and `cdk-nag`.
- **General AWS resource auditing** — use audit skills.
- **AWS SAM build/deploy** — use SAM CLI skills (this skill validates
  templates, not application deployment).

## How to invoke

### Slash command

```
/aws:operate-cfn-lint
```

Then provide: template file path, stack name, region, whether SAM
or nested stacks are involved, stack policy requirements.

### Natural language

Any of these routes to the same skill:

- "validate my CloudFormation template"
- "run cfn-lint on my template"
- "create a changeset before updating my stack"
- "scan my template with cfn-nag"
- "check for stack drift"
- "validate my SAM template"

### CLI routing

```bash
node cli/bin/cli.js route "cfn lint cloudformation template"
```

## Pipeline integration

This skill operates in **Phase 2 (Operate)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to validate or lint
CloudFormation templates. The output checklist feeds into deployment
pipelines and downstream audit skills.

## Example

```
You: /aws:operate-cfn-lint

     Validate template.yaml for stack my-app-stack in us-east-1.
     Run cfn-lint, validate-template, cfn-nag, and create a
     ChangeSet.

Skill:
  CFN_LINT: template.yaml → my-app-stack
  VERDICT: OPERATION_COMPLETED
  CHECKLIST:
    [✓] cfn-lint: PASSED (0 errors, 2 warnings)
    [✓] validate-template: PASSED
    [✓] cfn-nag: PASSED (0 critical, 1 warning)
    [✓] ChangeSet: 1 Add, 2 Modify, 0 Remove
    [✓] Stack policy: Enforced (AWS::RDS::DBInstance, AWS::S3::Bucket)
  VERIFICATION_COMMANDS:
    cfn-lint template.yaml
    cfn_nag_scan --input-path template.yaml
    aws cloudformation describe-change-set --change-set-name <cs-name> --stack-name my-app-stack --region us-east-1
```

## References

- Skill definition: `skills/cloudformation-cfn-lint-operator/SKILL.md`
- Linting and validation guide: `skills/cloudformation-cfn-lint-operator/references/linting-and-validation.md`
- Security and ChangeSet guide: `skills/cloudformation-cfn-lint-operator/references/security-and-changesets.md`
- Eval suite: `skills/cloudformation-cfn-lint-operator/evals/evals.json`
