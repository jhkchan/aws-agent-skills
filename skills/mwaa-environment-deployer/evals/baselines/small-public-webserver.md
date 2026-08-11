# Baseline (no-skill) — small-public-webserver

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the execution class
> sizing rationale, the 2-private-subnet-different-AZ verification, the
> S3 access path check, the requirements.txt version pinning guidance,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

You can create an MWAA environment like this:

```bash
aws mwaa create-environment \
  --name dev-airflow \
  --airflow-version 2.9.2 \
  --environment-class mw1.small \
  --source-bucket-arn arn:aws:s3:::my-mwaa-bucket \
  --dag-s3-path dags/ \
  --execution-role-arn arn:aws:iam::123456789012:role/MwaaExecutionRole \
  --network-configuration '{"SecurityGroupIds":["sg-mwaa123"],"SubnetIds":["subnet-aaa","subnet-bbb"]}'
```

Then wait for it to be available.
