# Diagnostic Commands — Kinesis Data Analytics Deployer

Pre-flight safety check listings moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Pre-flight safety checks (run before any deployment CLI) (moved from SKILL.md)

- **Confirm execution role exists and trusts
  `kinesisanalytics.amazonaws.com`.**
- **Confirm source Kinesis stream (or Firehose) exists and is ACTIVE.**
- **Confirm destination resource exists (Kinesis stream, Firehose, or
  S3 bucket).**
- **Confirm S3 code bucket has the pinned application code object.**
- **Confirm runtime environment is the latest stable Flink.**
- **Confirm service quota for KPUs is sufficient.**
- **Confirm CloudWatch log group exists (or will be created by KDA).**
- **Confirm VPC subnets exist (if private sources like MSK).**
- **Confirm Glue schema registry has the schema (if Avro/Protobuf).**
- **For existing applications, create a snapshot before code updates.**

Full CLI sequences for all checks in
`references/execution-and-capacity-guide.md`.

