# Baseline (no-skill) response: insufficient-context-need-table-name

This file captures what a generic assistant produces WITHOUT the
dynamodb-throttling-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

It sounds like your DynamoDB table is throttling. To help diagnose this,
I need more information:

1. What is the table name?
2. What AWS region is the table in?
3. What error message are you seeing? (e.g.,
   `ProvisionedThroughputExceededException`)
4. Is the throttling on reads or writes?
5. What is your current provisioned capacity?

Once you provide this, I can help you figure out the cause and suggest a
fix. Common causes include insufficient provisioned capacity, hot
partition keys, or expensive Scan operations.

In the meantime, you could try switching to on-demand billing mode to
see if that resolves the throttling:

```bash
aws dynamodb update-table --table-name <your-table> \
  --billing-mode PAY_PER_REQUEST
```
