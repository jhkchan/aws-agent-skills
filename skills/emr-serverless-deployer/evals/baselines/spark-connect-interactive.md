# Baseline (no-skill) — spark-connect-interactive

> This is the response a model produces **without** the skill definition.
> It creates the Spark application but does not configure the Spark
> Connect interactive endpoint. Users cannot connect from notebooks via
> the thin client protocol. It also misses pre-initialized capacity
> and the 60-minute auto-stop for interactive workloads.

---

Here are the commands to deploy your EMR Serverless Spark application:

```bash
aws emr-serverless create-application \
  --name analytics-spark-prod \
  --release-label emr-7.2.0 \
  --type SPARK \
  --auto-stop-configuration '{"enabled": true, "idleTimeoutMinutes": 15}'
```

Your analytics application should be available. You can set up
interactive access from the console.
