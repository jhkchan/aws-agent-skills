# Advanced Patterns — CloudFormation cfn-lint Operator

Load-on-demand deep dives moved verbatim from SKILL.md.

## Step 9 — Resource import and macro validation

**Resource import** brings existing AWS resources under CloudFormation
management. Each imported resource MUST have `DeletionPolicy: Retain`.
Not all resource types support import — check the support matrix.
Drift detection runs during import.

```bash
aws cloudformation create-change-set \
  --stack-name my-stack --change-set-name import-cs \
  --change-set-type IMPORT \
  --template-body file://template-import.yaml \
  --resources-to-import file://resources.json --region us-east-1
```

**Macro expansion:** macros transform template content via Lambda at
deployment time. cfn-lint and validate-template see the PRE-macro
template. Use `get-template-summary` to inspect the expanded output.

```bash
aws cloudformation get-template-summary \
  --template-body file://template-with-macro.yaml --region us-east-1
```

## Step 10 — IaC pipeline integration (gating logic and CodePipeline YAML)

**Pipeline gating logic:**
1. cfn-lint must pass (no errors).
2. cfn-nag must pass (no CRITICAL findings).
3. ChangeSet must be created (review required for replacements).
4. Execute ChangeSet only after manual approval.

```yaml
# CodePipeline Build stage with cfn-lint and cfn-nag gates
- Name: ValidateTemplate
  Actions:
    - Name: cfnLint
      ActionTypeId: { Category: Build, Owner: AWS, Provider: CodeBuild, Version: "1" }
      Configuration: { ProjectName: cfn-lint-project }
      RunOrder: 1
    - Name: cfnNag
      ActionTypeId: { Category: Build, Owner: AWS, Provider: CodeBuild, Version: "1" }
      Configuration: { ProjectName: cfn-nag-project }
      RunOrder: 2
    - Name: createChangeSet
      ActionTypeId: { Category: Deploy, Owner: AWS, Provider: CloudFormation, Version: "1" }
      Configuration:
        ActionMode: CHANGE_SET_REPLACE
        StackName: !Ref StackName
        ChangeSetName: pipeline-changeset
        Capabilities: CAPABILITY_NAMED_IAM
      RunOrder: 3
```

## Step 13 — Recent features

**Recent AWS features (2023-2026):**

- **cfn-lint enhanced resource specification coverage (2023-2024):**
  cfn-lint now covers all AWS resource specifications including
  newer services (AppRunner, Bedrock, Security Hub). Rules are
  auto-generated from the AWS resource specification JSON.

- **CloudFormation Hooks (2023-2024):** Hooks allow pre-deployment
  and post-deployment evaluation of template changes. Hooks run
  BEFORE a ChangeSet is executed, enabling proactive policy
  enforcement (e.g., block templates with unencrypted resources).

- **cfn-nag improved IAM analysis (2023-2024):** Enhanced IAM policy
  analysis in cfn-nag, including detection of privilege escalation
  patterns, unused IAM actions, and cross-account trust
  relationships.

- **Drift detection improvements (2023-2024):** Extended drift
  detection support to additional resource types (including
  CloudFront distributions, API Gateway REST APIs, and AppSync
  APIs). Previously, many resource types were not supported by drift
  detection.

- **ChangeSet nested stack visibility (2024-2025):** ChangeSet now
  shows changes within nested stacks, not just the parent stack.
  Previously, nested stack changes were opaque in the ChangeSet
  view.

- **SAM CLI cfn-lint integration (2024-2025):** The SAM CLI now
  integrates cfn-lint directly, running lint checks during
  `sam build` and `sam deploy` without requiring a separate cfn-lint
  invocation.
