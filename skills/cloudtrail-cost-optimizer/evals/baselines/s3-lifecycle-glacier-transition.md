# Baseline (no-skill) response: s3-lifecycle-glacier-transition

This file captures what a generic assistant produces WITHOUT the
cloudtrail-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, lifecycle tier schedule
with cost math, Glacier IR vs Deep Archive RTO rationale).

---

Your CloudTrail log bucket has 850 GB of logs in Standard storage with
no lifecycle policy. That's expensive — Standard is $0.023/GB-month
which is about $19.55/month just for storage. You should add a lifecycle
policy to move older logs to cheaper storage.

Something like this:

```
aws s3api put-bucket-lifecycle-configuration \
  --bucket cloudtrail-logs-standalone-us-east-1 \
  --lifecycle-configuration file://lifecycle.json
```

Where the lifecycle transitions logs to Glacier after some period. You
can also set an expiration rule to delete logs after your retention
period.
