# Baseline (no-skill) — large-config-overrides

> This is the response a model produces **without** the skill
> definition. It does not include Airflow configuration overrides, does
> not flag that parallelism=64 may exceed mw1.large worker capacity,
> omits KMS encryption and all CloudWatch Logs, and does not emit a
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Create the MWAA environment:

```bash
aws mwaa create-environment \
  --name enterprise-airflow \
  --airflow-version 2.9.2 \
  --environment-class mw1.large \
  --min-workers 2 \
  --max-workers 50 \
  --source-bucket-arn arn:aws:s3:::ent-mwaa-bucket \
  --dag-s3-path dags/ \
  --execution-role-arn arn:aws:iam::123456789012:role/MwaaEntRole \
  --network-configuration '{"SecurityGroupIds":["sg-ent-mwaa"],"SubnetIds":["subnet-ent-a","subnet-ent-b"]}'
```

The environment should be ready in about 30 minutes.
