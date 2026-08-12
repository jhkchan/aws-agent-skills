# Eval: nested-applications-composition

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — parent app nests two child SAR apps via AWS::Serverless::Application, CAPABILITY_AUTO_EXPAND required, child ARNs cited

## Prompt

Publish a parent serverless application named data-pipeline-suite.
The SAM template nests two child SAR applications:
arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor
(version 1.0.0) and
arn:aws:serverlessrepo:us-east-1:123456789012:apps/kinesis-forwarder
(version 2.0.0). README.md present. LICENSE present (Apache-2.0).
Semantic version 1.0.0. Private sharing. Author: Jacky Chan.
Region us-east-1.
