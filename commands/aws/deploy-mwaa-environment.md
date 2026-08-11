---
description: Create an Amazon MWAA (Managed Workflows for Apache Airflow) environment with production-grade defaults (execution class sizing, VPC subnet requirements, webserver access mode, S3 DAG bucket with requirements.txt and plugins, CloudWatch Logs, KMS encryption, Airflow configuration overrides, startup/stop time). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create mwaa environment"
  - "deploy mwaa environment"
  - "mwaa environment"
  - "managed airflow"
  - "mwaa execution class"
  - "mwaa vpc subnets"
  - "airflow requirements.txt"
  - "mwaa cloudwatch logs"
  - "mwaa webserver access"
  - "airflow plugin zip"
  - "mwaa configuration overrides"
  - "create airflow environment"
routes_to: mwaa-environment-deployer
---

# /aws:deploy-mwaa-environment

Activate the `mwaa-environment-deployer` skill and create an Amazon
Managed Workflows for Apache Airflow (MWAA) environment with
production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Execution class sizing (mw1.small/medium/large)
2. VPC subnet requirements (2 private in different AZs)
3. Webserver access mode (PUBLIC_ONLY vs PRIVATE_ONLY)
4. S3 DAG bucket setup (requirements.txt, plugins, startup script)
5. Create the environment (create-environment)
6. CloudWatch Logs (DagProcessing, Scheduler, Webserver, Worker)
7. Airflow configuration overrides
8. KMS encryption and IAM execution role
9. Startup/stop time scheduling
10. Recent features and best practices

## When to use

- You need to create an MWAA environment.
- You are sizing the execution class (mw1.small/medium/large).
- You need to configure VPC networking for MWAA.
- You need to set up the S3 DAG bucket with requirements.txt.
- You need to configure CloudWatch Logs for MWAA.
- You need Airflow configuration overrides.
- You need KMS encryption for MWAA.
- You need to choose webserver access mode.

## When NOT to use

- **Self-managed Airflow on EC2/ECS** — not an MWAA use case.
- **Amazon EMR scheduling** — use EMR-specific skills.
- **AWS Step Functions** — different orchestration service.
- **Apache Airflow on EKS** — self-managed, not MWAA.

## How to invoke

### Slash command

```
/aws:deploy-mwaa-environment
```

Then provide: environment name, Airflow version, execution class, min/
max workers, webserver access mode, VPC subnets (2 private in different
AZs), security group, S3 DAG bucket, requirements.txt path, plugins
path, IAM role ARN, KMS key ARN, CloudWatch log levels, tags.

### Natural language

Any of these routes to the same skill:

- "create an MWAA environment"
- "set up managed Airflow on AWS"
- "configure mw1.medium environment with PRIVATE_ONLY webserver"
- "deploy Airflow with requirements.txt and plugins"
- "size MWAA execution class for 50 concurrent DAGs"

### CLI routing

```bash
node cli/bin/cli.js route "create an mwaa environment"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create an MWAA
environment. The output checklist feeds into verification pipelines
and downstream audit skills.

## Example

```
You: /aws:deploy-mwaa-environment

     Create an MWAA environment named prod-airflow. Airflow 2.9.2,
     mw1.medium, 1-25 workers. PRIVATE_ONLY webserver. VPC vpc-prod111
     with subnets subnet-prov-a (us-east-1a) and subnet-prov-b
     (us-east-1b). All CloudWatch Logs. KMS key abcd1234. 15 DAGs.

Skill:
  MWAA_ENVIRONMENT: prod-airflow (mw1.medium, Airflow 2.9.2)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Execution class: mw1.medium
    [✓] VPC subnets: 2 private, different AZs — PASS
    [✓] Webserver: PRIVATE_ONLY
    [✓] CloudWatch Logs: all 4 types enabled
    [✓] KMS: configured
  VERIFICATION_COMMANDS:
    aws mwaa get-environment --name prod-airflow --region us-east-1
    aws mwaa list-environments --region us-east-1
    aws s3 ls s3://prod-mwaa-dags/dags/
```

## References

- Skill definition: `skills/mwaa-environment-deployer/SKILL.md`
- VPC and networking guide: `skills/mwaa-environment-deployer/references/vpc-and-networking.md`
- DAGs and plugins guide: `skills/mwaa-environment-deployer/references/dags-and-plugins.md`
- Eval suite: `skills/mwaa-environment-deployer/evals/evals.json`
