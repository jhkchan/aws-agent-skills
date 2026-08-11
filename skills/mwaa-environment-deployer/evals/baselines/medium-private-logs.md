# Baseline (no-skill) — medium-private-logs

> This is the response a model produces **without** the skill
> definition. It creates the environment but omits the PRIVATE_ONLY
> webserver mode flag, forgets to enable all 4 CloudWatch Log types,
> does not configure KMS encryption, and does not emit a READY_TO_DEPLOY
> checklist. Generated for with-skill-vs-baseline comparison.

---

Create the MWAA environment:

```bash
aws mwaa create-environment \
  --name prod-airflow \
  --airflow-version 2.9.2 \
  --environment-class mw1.medium \
  --source-bucket-arn arn:aws:s3:::prod-mwaa-dags \
  --dag-s3-path dags/ \
  --execution-role-arn arn:aws:iam::123456789012:role/MwaaProdRole \
  --network-configuration '{"SecurityGroupIds":["sg-prod-mwaa"],"SubnetIds":["subnet-prov-a","subnet-prov-b"]}'
```

The webserver should be accessible after creation.
