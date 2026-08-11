# Baseline (no-skill) — missing-subnet-requirements

> This is the response a model produces **without** the skill
> definition. It proceeds to create the MWAA environment with only 1
> subnet, which will fail at the API call. Does not flag that MWAA
> requires 2 private subnets in different AZs. Does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Sure, here's how to create the environment:

```bash
aws mwaa create-environment \
  --name test-airflow \
  --airflow-version 2.9.2 \
  --environment-class mw1.small \
  --source-bucket-arn arn:aws:s3:::test-mwaa-bucket \
  --dag-s3-path dags/ \
  --execution-role-arn arn:aws:iam::123456789012:role/MwaaTestRole \
  --network-configuration '{"SecurityGroupIds":["sg-test-mwaa"],"SubnetIds":["subnet-single"]}'
```

Wait for the environment to become available.
