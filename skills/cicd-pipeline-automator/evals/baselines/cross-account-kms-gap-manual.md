# Baseline (no-skill) response: cross-account-kms-gap-manual

This file captures what a generic assistant produces WITHOUT the
cicd-pipeline-automator skill loaded.

---

To set up cross-account deployment, you need:

1. A pipeline in the source account (111111111111).
2. A deploy role in the target account (222222222222) that the
   pipeline can assume.
3. An artifact bucket that both accounts can access.

Use this CloudFormation to create the cross-account pipeline:

```yaml
# Basic cross-account pipeline
Resources:
  Pipeline:
    Type: AWS::CodePipeline::Pipeline
    Properties:
      RoleArn: !GetAtt PipelineRole.Arn
      Stages: [...]
```

Make sure the deploy role has permissions to deploy CloudFormation
in the target account.
