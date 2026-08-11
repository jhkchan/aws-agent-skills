# Eval prompt: manual-approval-flow

Design a deployment plan for a V2 pipeline with a manual approval gate
between Build and Deploy stages. Emit the standard VERDICT block.

Requirements:

- Pipeline type: V2
- Region: us-east-1
- Pipeline name: my-service-gated-pipeline
- Source: CodeCommit repository `my-service`, branch `main`
- Build: CodeBuild `my-service-build`, exports IMAGE_URI
- Approval stage between Build and Deploy:
  - ExternalEntityLink: https://internal.example.com/change-record/CHG12345
  - CustomData: "Approve to deploy to prod. Reviewer: oncall@example.com"
  - NotificationArn (SNS topic):
    arn:aws:sns:us-east-1:111111111111:prod-approval
- Deploy: CloudFormation CREATE_REPLACE on `prod-my-service`
- Trigger: branch filter main only
- Artifact bucket: my-pipeline-artifacts (existing, KMS-encrypted,
  block-public-access)
- Pipeline role: my-pipeline-role (existing)

Existing-account context: the SNS topic `prod-approval` exists with
email and Slack subscriptions. The CodeBuild project, CloudFormation
stack, KMS key, and pipeline IAM role all exist. The pipeline does
NOT exist yet — the skill should emit create-pipeline as the final
command. The operator wants the skill to warn about the lack of
approval timeout enforcement and suggest a scheduled Lambda for
auto-rejecting stale approvals.
