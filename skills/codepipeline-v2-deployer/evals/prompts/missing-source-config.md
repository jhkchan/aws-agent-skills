# Eval prompt: missing-source-config

Design a deployment plan for a V2 pipeline. Emit the standard VERDICT
block.

Requirements:

- Pipeline type: V2
- Region: us-east-1
- Build: CodeBuild `my-service-build`
- Deploy: CloudFormation CREATE_REPLACE on `prod-my-service`

The user did NOT specify: source (CodeCommit / S3 / GitHub via
CodeConnections), repository name, branch, or trigger configuration.
The skill must catch this as PREREQUISITES_MISSING and emit a specific
citation of the missing source field. Do not assume CodeCommit by
default — flag the gap explicitly.
