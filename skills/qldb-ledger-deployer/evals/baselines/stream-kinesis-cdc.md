# Baseline (no-skill) — stream-kinesis-cdc

> This is the response a model produces **without** the skill
> definition. It creates the ledger and mentions Kinesis streaming but
> does not detail the IAM role trust policy (QLDB service principal),
> does not explain the stream start/end time semantics, does not note
> aggregation options, and omits the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the ledger:

```bash
aws qldb create-ledger \
  --name realtime-events \
  --permissions-mode STANDARD \
  --deletion-protection \
  --region us-east-1
```

Then stream to Kinesis:

```bash
aws qldb stream-journal-to-kinesis \
  --ledger-name realtime-events \
  --inclusive-start-time 2026-08-05T00:00:00Z \
  --stream-name events-cdc
```

The Kinesis stream should receive the data.
