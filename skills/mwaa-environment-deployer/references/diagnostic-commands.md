# Diagnostic and Pre-flight Commands — MWAA Environment Deployer

## Monitor environment status

**Monitor environment status:**

```bash
aws mwaa get-environment \
  --name "production-airflow" \
  --query 'Environment.Status' \
  --region us-east-1
# Expected: CREATING → CREATING_SNAPSHOT → AVAILABLE (or FAILED)
```

## Step 9 — startup/stop schedule commands

```bash
aws mwaa update-environment \
  --name "dev-airflow" \
  --startup-time "08:00" \
  --shutdown-time "20:00" \
  --region us-east-1
```

