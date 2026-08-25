# Remediation Procedures — Redshift Cluster Auditor


## Per-verdict remediation playbooks

### For PUBLIC — public accessibility (Step 1)

1. **If public access is NOT intentional:** set
   `PubliclyAccessible: false` and reboot. CLI:
   ```bash
   aws redshift modify-cluster --cluster-identifier <id> \
     --no-publicly-accessible --profile <p>
   aws redshift reboot-cluster --cluster-identifier <id> --profile <p>
   ```
   This requires a maintenance window; queries in flight are terminated.
2. **If public access IS intentional** (rare — partner-data workload
   with no VPC peering): restrict the SG to the specific partner
   CIDRs. Do NOT leave `0.0.0.0/0` on the cluster port. Require SSL.
3. **Verify** with `aws redshift describe-clusters --cluster-identifier
   <id>` that `PubliclyAccessible: false` is effective.
4. **Assume breach.** Audit CloudTrail for `ModifyCluster` calls
   during the exposure window. Check S3 audit logs (if enabled) for
   unexpected source IPs in STL_CONNECTION_LOG.

### For NO_ENCRYPTION — encryption-at-rest (Step 2)

There is NO in-place remediation. The migration workflow:

1. Provision a new encrypted cluster (preferably RA3 with a CMK):
   ```bash
   aws redshift create-cluster --cluster-identifier <id>-encrypted \
     --node-type ra3.xlplus --number-of-nodes <n> \
     --master-username <u> --master-user-password <pwd> \
     --encrypted --kms-key-id <cmk-arn> \
     --cluster-subnet-group-name <sg> --vpc-security-group-ids <sg-id> \
     --cluster-parameter-group-name <custom-pg-with-require-ssl> \
     --publicly-accessible false --enhanced-vpc-routing --profile <p>
   ```
2. `UNLOAD` from the old cluster to S3 (Parquet recommended):
   ```sql
   UNLOAD ('SELECT * FROM schema.table')
   TO 's3://migration-bucket/<id>/'
   IAM_ROLE '<role-arn>' FORMAT PARQUET ENCRYPTED;
   ```
3. `COPY` into the new cluster:
   ```sql
   COPY schema.table FROM 's3://migration-bucket/<id>/'
   IAM_ROLE '<role-arn>' FORMAT PARQUET;
   ```
4. Validate row counts, validate downstream BI dashboards, redirect
   DNS / connection strings.
5. Decommission the old cluster only after validation:
   ```bash
   aws redshift delete-cluster --cluster-identifier <id> \
     --final-cluster-snapshot-identifier final-<id>-$(date +%s)
   ```
   Always take a final manual snapshot before deletion.

### For NO_SSL — require_ssl enforcement (Step 3)

1. Create a custom parameter group:
   ```bash
   aws redshift create-cluster-parameter-group \
     --parameter-group-name require-ssl-pg \
     --parameter-group-family redshift-1.0 \
     --description "Custom PG with require_ssl" --profile <p>
   aws redshift modify-cluster-parameter-group \
     --parameter-group-name require-ssl-pg \
     --parameters ParameterName=require_ssl,ParameterValue=true \
     --profile <p>
   ```
2. Associate with the cluster (requires reboot):
   ```bash
   aws redshift modify-cluster --cluster-identifier <id> \
     --cluster-parameter-group-name require-ssl-pg --profile <p>
   aws redshift reboot-cluster --cluster-identifier <id> --profile <p>
   ```
3. Verify: `aws redshift describe-cluster-parameters
   --parameter-group-name require-ssl-pg` shows `require_ssl: true`.

### For NO_AUDIT_LOG — S3 audit logging (Step 4)

1. Enable logging:
   ```bash
   aws redshift enable-logging --cluster-identifier <id> \
     --log-destination-name S3 --bucket-name <audit-bucket> \
     --s3-key-prefix redshift/<id>/ --profile <p>
   ```
2. Verify: `aws redshift describe-logging-status --cluster-identifier
   <id>` shows `LoggingEnabled: true`.
3. Verify bucket ownership and retention policy separately — S3 audit
   logs are only useful if the bucket is tamper-evident (object-lock
   recommended).
4. For full forensic coverage, also set
   `enable_user_activity_logging: true` in the parameter group.

### For CONFIG_GAP — sub-finding remediation

**Automated snapshots disabled (retention 0):**
```bash
aws redshift modify-cluster --cluster-identifier <id> \
  --automated-snapshot-retention-period 7 --profile <p>
```
Re-enable within the snapshot window to recover PITR. Compliance
postures typically require 7-35 days.

**Enhanced VPC routing off:**
```bash
aws redshift modify-cluster --cluster-identifier <id> \
  --enhanced-vpc-routing --profile <p>
aws redshift reboot-cluster --cluster-identifier <id> --profile <p>
```
After enabling, COPY/UNLOAD traffic flows through your VPC — verify S3
Gateway VPC endpoint exists or COPY/UNLOAD may fail.

**SG with 0.0.0.0/0 on cluster port:**
```bash
aws ec2 revoke-security-group-ingress --group-id <sg-id> \
  --ip-permissions IpProtocol=tcp,FromPort=<cluster-port>,ToPort=<cluster-port>,IpRanges=[{CidrIp=0.0.0.0/0}] \
  --profile <p>
aws ec2 authorize-security-group-ingress --group-id <sg-id> \
  --ip-permissions IpProtocol=tcp,FromPort=<cluster-port>,ToPort=<cluster-port>,IpRanges=[{CidrIp=10.0.0.0/16}] \
  --profile <p>
```
Verify no other resource shares this SG before revoking.

**User-activity logging off:** set `enable_user_activity_logging: true`
in the custom parameter group (same workflow as require_ssl).

### For OK

1. No remediation required.
2. Recommend periodic re-audit (configuration drift is common on
   long-running clusters).
3. Recommend cross-referencing the KMS key policy via the
   kms-key-policy-auditor skill when a CMK is in use.
4. Recommend verifying the audit-log S3 bucket's object-lock / retention
   policy separately.
5. For multi-AZ clusters, verify the `MultiAZ` deployment status is
   still in sync across AZs.
