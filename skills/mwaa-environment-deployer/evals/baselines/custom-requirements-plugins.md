# Baseline (no-skill) — custom-requirements-plugins

> This is the response a model produces **without** the skill
> definition. It does not verify that requirements.txt packages are
> exact-pinned, does not check Python compatibility, does not specify
> the plugins ZIP path in the create-environment call, and does not
> emit a READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Create the MWAA environment:

```bash
aws mwaa create-environment \
  --name etl-airflow \
  --airflow-version 2.9.2 \
  --environment-class mw1.medium \
  --source-bucket-arn arn:aws:s3:::etl-mwaa-bucket \
  --dag-s3-path dags/ \
  --requirements-s3-path requirements.txt \
  --execution-role-arn arn:aws:iam::123456789012:role/MwaaEtlRole \
  --network-configuration '{"SecurityGroupIds":["sg-etl-mwaa"],"SubnetIds":["subnet-etl-a","subnet-etl-b"]}'
```

Upload your requirements.txt and plugins to the bucket.
