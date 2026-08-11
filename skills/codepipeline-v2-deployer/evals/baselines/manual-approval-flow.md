# Baseline (no-skill) response: manual-approval-flow

This file captures what a generic assistant produces WITHOUT the
codepipeline-v2-deployer skill loaded. The contrast proves the skill
adds the manual approval action contract (ExternalEntityLink,
CustomData, NotificationArn), the "no enforced timeout" warning, and
the suggestion to use a scheduled Lambda for auto-rejecting stale
approvals.

---

Here's a plan for your V2 pipeline with manual approval.

Architecture:

- V2 pipeline in us-east-1
- Source: CodeCommit my-service
- Build: CodeBuild
- Approval gate
- Deploy: CloudFormation

Steps:

1. Create the pipeline.
2. Add an approval action between Build and Deploy.
3. Configure SNS for notifications.

For the approval action, you can add an ExternalEntityLink to your
change ticket and CustomData with reviewer instructions.

Commands:

```
aws codepipeline create-pipeline --cli-input-json file://pipeline.json
```

The pipeline will wait at the approval step until someone clicks
Approve in the console.
