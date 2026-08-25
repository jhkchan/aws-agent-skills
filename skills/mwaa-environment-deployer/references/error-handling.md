# Error Handling — MWAA Environment Deployer

### Environment creation FAILED
- Check status via `aws mwaa get-environment --query 'Environment.Status'`.
- Common causes: subnets not in different AZs, IAM role missing
  permissions, S3 bucket in wrong region, security group rules incorrect.

### DAGs not executing
- Check DagProcessingLogs for import errors. Verify the DAG file has a
  valid `DAG` object. Verify `dag_id` is unique across all DAGs.

### Tasks queued but not running
- Check WorkerLogs for worker startup failures (often requirements.txt
  package issues). Check `QueuedTasks` metric — if consistently > 0,
  increase max workers or upgrade execution class.

### requirements.txt packages failing to install
- Check DagProcessingLogs for pip install errors. Verify version pins
  are compatible with the Airflow and Python versions. Use
  `psycopg2-binary` instead of `psycopg2`. Test locally with the MWAA
  local runner Docker image.

### Webserver inaccessible (PRIVATE_ONLY mode)
- Verify VPN/Direct Connect to the VPC. Check security group inbound
  443 from the VPN/DX subnet. Verify DNS resolution within the VPC.

