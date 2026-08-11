# Eval: missing-logging-on-async

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — async Express without CloudWatch Logs is a NEVER pattern

## Prompt

Provision an async Express Workflow "batch-loader" (account
123456789012, region us-east-1) triggered by EventBridge
rate(1 minute). I will attach CloudWatch Logs later — skip
the loggingConfiguration for now. The execution role is
scoped to lambda:InvokeFunction on function:loader. Add the
EventBridge target role. Make sure I can debug failures.
