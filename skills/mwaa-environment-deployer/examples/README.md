# End-to-End Example: MWAA Environment Deployment

A walkthrough showing how to use the `mwaa-environment-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an mw1.medium MWAA environment with PRIVATE_ONLY
webserver, all CloudWatch log types enabled, KMS encryption, custom
requirements.txt, and 15 DAGs. The environment needs:

- Environment name: prod-airflow
- Airflow version: 2.9.2
- Execution class: mw1.medium (min 1, max 25 workers)
- Webserver: PRIVATE_ONLY
- VPC: vpc-prod111 (subnet-prov-a in us-east-1a, subnet-prov-b in
  us-east-1b — both private, with S3 VPC endpoint)
- Security group: sg-prod-mwaa
- S3 DAG bucket: s3://prod-mwaa-dags (15 DAGs in /dags/)
- requirements.txt: 7 exact-pinned packages
- KMS: arn:aws:kms:us-east-1:123456789012:key/abcd1234
- All CloudWatch Logs enabled
- IAM role: arn:aws:iam::123456789012:role/MwaaProdRole
- Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-mwaa-environment
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an MWAA environment named prod-airflow. Airflow 2.9.2,
      mw1.medium with 1-25 workers. PRIVATE_ONLY webserver. VPC
      vpc-prod111 with subnets subnet-prov-a and subnet-prov-b.
      All CloudWatch Logs. KMS encryption. 15 DAGs."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an mwaa environment"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
MWAA_ENVIRONMENT: prod-airflow (mw1.medium, Airflow 2.9.2)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Environment name: prod-airflow
  [✓] Airflow version: 2.9.2
  [✓] Execution class: mw1.medium
  [✓] Min workers: 1, Max workers: 25
  [✓] Webserver access: PRIVATE_ONLY
  [✓] VPC subnets: subnet-prov-a (us-east-1a), subnet-prov-b (us-east-1b) — private, different AZs
  [✓] Security group: sg-prod-mwaa (inbound 443+5432 self, outbound 443)
  [✓] S3 access path: S3 VPC endpoint — PASS
  [✓] S3 DAG bucket: s3://prod-mwaa-dags — /dags/ folder with 15 DAGs
  [✓] requirements.txt: s3://prod-mwaa-bucket/requirements.txt (7 packages, exact-pinned)
  [✓] Plugins ZIP: none
  [✓] IAM execution role: arn:aws:iam::123456789012:role/MwaaProdRole
  [✓] KMS key: arn:aws:kms:us-east-1:123456789012:key/abcd1234
  [✓] CloudWatch Logs: DagProcessing=INFO, Scheduler=INFO, Webserver=WARNING, Worker=INFO
  [✓] Startup/stop time: 24/7
  [✓] Tags: Environment=production, Compliance=HIPAA
VERIFICATION_COMMANDS:
  aws mwaa get-environment --name prod-airflow --region us-east-1
  aws mwaa list-environments --region us-east-1
  aws s3 ls s3://prod-mwaa-dags/dags/
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Verify VPC subnets are in different AZs
aws ec2 describe-subnets \
  --subnet-ids subnet-prov-a subnet-prov-b \
  --query 'Subnets[*].{SubnetId:SubnetId,AZ:AvailabilityZone}' \
  --region us-east-1

# Step 2: Upload DAGs to S3
aws s3 sync ./dags/ s3://prod-mwaa-dags/dags/

# Step 3: Upload requirements.txt
aws s3 cp requirements.txt s3://prod-mwaa-dags/requirements.txt

# Step 4: Create the MWAA environment
ENV_ARN=$(aws mwaa create-environment \
  --name "prod-airflow" \
  --airflow-version "2.9.2" \
  --environment-class "mw1.medium" \
  --min-workers 1 \
  --max-workers 25 \
  --webserver-access-mode "PRIVATE_ONLY" \
  --source-bucket-arn arn:aws:s3:::prod-mwaa-dags \
  --dag-s3-path "dags/" \
  --requirements-s3-path "requirements.txt" \
  --execution-role-arn arn:aws:iam::123456789012:role/MwaaProdRole \
  --network-configuration '{"SecurityGroupIds":["sg-prod-mwaa"],"SubnetIds":["subnet-prov-a","subnet-prov-b"]}' \
  --kms-key arn:aws:kms:us-east-1:123456789012:key/abcd1234 \
  --logging-configuration '{
    "DagProcessingLogs":{"Enabled":true,"LogLevel":"INFO"},
    "SchedulerLogs":{"Enabled":true,"LogLevel":"INFO"},
    "WebserverLogs":{"Enabled":true,"LogLevel":"WARNING"},
    "WorkerLogs":{"Enabled":true,"LogLevel":"INFO"}
  }' \
  --region us-east-1 \
  --query 'EnvironmentArn' --output text)

# Step 5: Wait for environment to become AVAILABLE (20-30 minutes)
aws mwaa get-environment \
  --name "prod-airflow" \
  --query 'Environment.Status' \
  --region us-east-1
# Expected: CREATING → CREATING_SNAPSHOT → AVAILABLE
```

---

## Step 4 — Post-deployment verification

```bash
# Environment status — should be AVAILABLE
aws mwaa get-environment \
  --name prod-airflow \
  --query 'Environment.{Status:Status,Class:EnvironmentClass,Webserver:WebserverAccessMode}' \
  --region us-east-1

# Check CloudWatch Logs are being written
aws logs describe-log-streams \
  --log-group-name /aws/mwaa/environment/prod-airflow/Scheduler \
  --limit 5 \
  --region us-east-1

# Get the webserver URL (requires IAM CreateWebLoginToken permission)
aws mwaa create-web-login-token \
  --name prod-airflow \
  --region us-east-1 \
  --query 'WebServerHostname' --output text
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Subnet count | Accepts 1 subnet | Requires 2 private in different AZs | MWAA distributes workers across AZs for HA |
| S3 access path | Not checked | NAT Gateway or S3 VPC endpoint verified | Without S3 access, workers cannot pull DAGs |
| Execution class | Defaults to mw1.large | Sized by concurrent DAG/task count | Over-sizing wastes $1200/month for dev |
| requirements.txt | Unpinned versions | Exact version pins verified | Loose constraints cause non-reproducible failures |
| CloudWatch Logs | Not enabled | All 4 log types enabled at creation | Without logs, troubleshooting is impossible |
| Webserver mode | Defaults to PUBLIC_ONLY | PRIVATE_ONLY for compliance | PUBLIC_ONLY exposes webserver to internet |
| KMS encryption | Not configured | KMS key for metadata DB, volumes, logs | Without CMK, data uses AWS-managed key |
| Airflow config | Default parallelism | Sized to execution class capacity | Excessive parallelism causes task queuing |

---

## Related artifacts

- **Skill definition:** `skills/mwaa-environment-deployer/SKILL.md`
- **VPC and networking guide:** `skills/mwaa-environment-deployer/references/vpc-and-networking.md`
- **DAGs and plugins guide:** `skills/mwaa-environment-deployer/references/dags-and-plugins.md`
- **Slash command:** `commands/aws/deploy-mwaa-environment.md`
- **Eval suite:** `skills/mwaa-environment-deployer/evals/evals.json`
- **Legacy test cases:** `skills/mwaa-environment-deployer/eval/test-cases.yaml`
