# Baseline (no-skill) — topic-rule-sql-timestream

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the fact that the SQL
> evaluates against the message payload (not a database), the IAM
> role permissions for Timestream, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create a topic rule:

```bash
aws iot create-topic-rule \
  --rule-name telemetry-to-timestream \
  --topic-rule-payload '{"sql":"SELECT * FROM '\''device/+/telemetry'\''"}'
```
