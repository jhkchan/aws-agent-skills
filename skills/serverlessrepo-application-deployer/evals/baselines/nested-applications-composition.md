# Baseline (no-skill) — nested-applications-composition

> This is the response a model produces **without** the skill
> definition. It writes the nested application template but does
> not flag CAPABILITY_AUTO_EXPAND as required (deploy will fail
> without it), does not verify that the child apps are published
> and shared, and omits the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Here is the template with nested apps:

```yaml
Resources:
  S3Processor:
    Type: AWS::Serverless::Application
    Properties:
      Location:
        ApplicationId: arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor
        SemanticVersion: 1.0.0
  KinesisForwarder:
    Type: AWS::Serverless::Application
    Properties:
      Location:
        ApplicationId: arn:aws:serverlessrepo:us-east-1:123456789012:apps/kinesis-forwarder
        SemanticVersion: 2.0.0
```

Then publish and deploy.
