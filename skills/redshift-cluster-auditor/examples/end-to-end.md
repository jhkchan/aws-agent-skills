# End-to-end usage scenario: redshift-cluster-auditor

A walkthrough showing the skill auditing a production Redshift cluster
that fails multiple dimensions simultaneously — public accessibility,
encryption disabled, default parameter group with require_ssl off, audit
logging off, and enhanced VPC routing off — demonstrating verdict
aggregation (PUBLIC wins), the encryption-is-immutable insight, and the
multi-step migration remediation workflow.

## Input (user prompt)

> Review this Redshift cluster before our quarterly compliance review.
> It powers the customer-analytics warehouse and stores two years of
> purchase history.

```
Cluster identifier: prod-customer-analytics
Cluster ARN: arn:aws:redshift:us-east-1:111111111111:cluster:prod-customer-analytics
Cluster metadata (describe-clusters):
  ClusterStatus: available
  NumberOfNodes: 4
  NodeType: ra3.4xlarge
  PubliclyAccessible: true
  Encrypted: false
  KmsKeyId: (none)
  EnhancedVPCRouting: false
  ClusterParameterGroupName: default.redshift-1.0
  ClusterParameterGroupStatus: in-sync
  AutomatedSnapshotRetentionPeriod: 1
  ElasticIpStatus: {ElasticIp: 203.0.113.42, Status: attached}
  VpcSecurityGroups: [{VpcSecurityGroupId: sg-0a1b2c3d4e5f6g7h8, Status: active}]
  Endpoint: {Address: prod-customer-analytics.c1abc.us-east-1.redshift.amazonaws.com, Port: 5439}

Parameter group parameters (default.redshift-1.0):
  - require_ssl = false (Source: engine-default)
  - enable_user_activity_logging = false (Source: engine-default)

Logging status (describe-logging-status):
  LoggingEnabled: false

Security group sg-0a1b2c3d4e5f6g7h8 ingress rules:
  - tcp 5439-5439 from 0.0.0.0/0
```

## Skill output

```text
CLUSTER: prod-customer-analytics
VERDICT: PUBLIC
REASON: PubliclyAccessible is true AND an Elastic IP (203.0.113.42) is
attached, placing the cluster on the public internet on TCP 5439 with a
stable, DNS-portable endpoint (Step 1). Encryption is also disabled,
require_ssl is the engine default, audit logging is off, and enhanced
VPC routing is off — every dimension fails.
FINDINGS:
  - [PUBLIC] PubliclyAccessible: true with ElasticIp 203.0.113.42 — stable
    internet endpoint on TCP 5439 (Step 1). Single-node-style exposure of a
    4-node production warehouse.
  - [NO_ENCRYPTION] Encrypted: false — data-at-rest is plaintext; snapshots
    inherit the unencrypted state (Step 2). KMS key irrelevant until
    encryption is enabled.
  - [NO_SSL] require_ssl: false in default.redshift-1.0 with Source
    engine-default — operator has not hardened this; default PG is read-only
    and cannot be modified in place (Step 3).
  - [NO_AUDIT_LOG] LoggingEnabled: false — no S3 audit trail; CloudTrail
    covers only control-plane events, not SQL queries (Step 4).
  - [CONFIG_GAP] AutomatedSnapshotRetentionPeriod: 1 — engine default;
    PCI/HIPAA typically require 7+ days (Step 5).
  - [CONFIG_GAP] EnhancedVPCRouting: false — COPY/UNLOAD traffic bypasses
    VPC SGs, NACLs, and VPC endpoints (Step 5).
  - [CONFIG_GAP] enable_user_activity_logging: false — STL_QUERY retains
    query text for only ~3-7 days; no long-horizon forensic export (Step 5).
  - [CONFIG_GAP] SG sg-0a1b2c3d4e5f6g7h8 has 0.0.0.0/0 on TCP 5439 —
    future flip of PubliclyAccessible instantly exposes the cluster (Step 5).
REMEDIATION:
  1. PUBLIC — Set PubliclyAccessible to false immediately. This requires
     a client reboot; in-flight queries will be terminated.
       aws redshift modify-cluster --cluster-identifier prod-customer-analytics \
         --no-publicly-accessible --profile <p>
       aws redshift reboot-cluster --cluster-identifier prod-customer-analytics --profile <p>
     Detach the Elastic IP via the EC2 console if it is no longer needed.
  2. PUBLIC — Assume breach. Audit S3 audit logs (if any exist) and
     CloudTrail for unexpected source IPs in the STL_CONNECTION_LOG
     view during the exposure window. Rotate database credentials.
  3. NO_ENCRYPTION — Plan an encryption migration (MULTI-DAY, not a CLI
     toggle). Encryption is immutable on an existing cluster:
     (a) Provision a new encrypted cluster with a CMK.
     (b) UNLOAD from the old cluster to S3 (Parquet, encrypted).
     (c) COPY into the new cluster.
     (d) Validate row counts + downstream BI dashboards.
     (e) Redirect DNS / connection strings.
     (f) Decommission the old cluster with a final manual snapshot.
  4. NO_SSL — Create a custom parameter group with require_ssl=true,
     associate it with the cluster, and reboot for the change to take
     effect. The default PG cannot be modified.
       aws redshift create-cluster-parameter-group \
         --parameter-group-name prod-analytics-pg \
         --parameter-group-family redshift-1.0 \
         --description "Custom PG for prod-customer-analytics" --profile <p>
       aws redshift modify-cluster-parameter-group \
         --parameter-group-name prod-analytics-pg \
         --parameters \
           ParameterName=require_ssl,ParameterValue=true \
           ParameterName=enable_user_activity_logging,ParameterValue=true \
         --profile <p>
       aws redshift modify-cluster --cluster-identifier prod-customer-analytics \
         --cluster-parameter-group-name prod-analytics-pg --profile <p>
       aws redshift reboot-cluster --cluster-identifier prod-customer-analytics --profile <p>
  5. NO_AUDIT_LOG — Enable S3 audit logging to a tamper-evident bucket
     (object-lock recommended):
       aws redshift enable-logging --cluster-identifier prod-customer-analytics \
         --log-destination-name S3 --bucket-name audit-logs-111111111111 \
         --s3-key-prefix redshift/prod-customer-analytics/ --profile <p>
  6. CONFIG_GAP — Raise snapshot retention and enable EnhancedVPCRouting
     (both require reboots):
       aws redshift modify-cluster --cluster-identifier prod-customer-analytics \
         --automated-snapshot-retention-period 7 --enhanced-vpc-routing --profile <p>
       aws redshift reboot-cluster --cluster-identifier prod-customer-analytics --profile <p>
     After enabling EnhancedVPCRouting, verify an S3 Gateway VPC endpoint
     exists in the cluster's VPC or COPY/UNLOAD may fail.
  7. CONFIG_GAP — Restrict the SG ingress to the corporate CIDR:
       aws ec2 revoke-security-group-ingress --group-id sg-0a1b2c3d4e5f6g7h8 \
         --ip-permissions IpProtocol=tcp,FromPort=5439,ToPort=5439,IpRanges=[{CidrIp=0.0.0.0/0}] \
         --profile <p>
       aws ec2 authorize-security-group-ingress --group-id sg-0a1b2c3d4e5f6g7h8 \
         --ip-permissions IpProtocol=tcp,FromPort=5439,ToPort=5439,IpRanges=[{CidrIp=10.0.0.0/16}] \
         --profile <p>
     Verify no other resource shares this SG first (aws ec2
     describe-network-interfaces --groups sg-0a1b2c3d4e5f6g7h8).
```

## What the skill caught that a generic assistant misses

1. **The verdict priority is explicit and aggregate.** A generic
   assistant lists six issues in arbitrary order. The skill applies the
   ordered classification (PUBLIC > NO_ENCRYPTION > NO_SSL >
   NO_AUDIT_LOG > CONFIG_GAP > OK) and emits a single deterministic
   verdict (PUBLIC) while preserving every finding in the FINDINGS list.
   This is what makes the skill auditable and CI-assertable.

2. **The encryption-is-immutable insight.** A generic assistant says
   "enable encryption." The skill explains that Redshift encryption is
   fixed at cluster creation — there is no `modify-cluster --encrypted`
   flag — and provides the full UNLOAD/COPY migration workflow with the
   correct ordering (provision, unload, copy, validate, redirect,
   decommission). This is the difference between a 30-second CLI fix and
   a multi-day migration plan.

3. **The default-PG-is-read-only insight.** A generic assistant says
   "set require_ssl to true." The skill explains that the default
   parameter group cannot be modified — the operator must create a
   custom PG, associate it, AND reboot. Without this, the operator
   attempts `modify-cluster-parameter-group` on `default.redshift-1.0`
   and the API call fails.

4. **The CloudTrail-doesn't-cover-SQL insight.** A generic assistant
   says "CloudTrail covers your audit needs." The skill explains that
   CloudTrail logs only Redshift control-plane events (CreateCluster,
   ModifyCluster) — SQL query activity requires `enable-logging` (S3
   audit logs) AND `enable_user_activity_logging` (parameter) for full
   forensic coverage.

5. **The EnhancedVPCRouting data-path insight.** A generic assistant
   says "enhanced VPC routing is off, consider enabling it." The skill
   explains that without it, COPY/UNLOAD traffic to S3 traverses the
   public AWS network path, bypassing VPC SGs, NACLs, and VPC endpoints
   — the data path is not subject to network controls even though the
   cluster endpoint is private. Privacy of the cluster endpoint and
   privacy of the bulk-transfer data path are independent concerns.

6. **The snapshot retention 0 data-loss insight.** A generic assistant
   says "set retention to 7." The skill warns that setting retention to
   0 does not just stop future snapshots — Redshift immediately begins
   expiring existing automated snapshots within the next snapshot
   window. Operators setting retention to 0 to "save cost" without
   first converting critical automated snapshots to manual lose PITR
   irreversibly within hours.

7. **The Elastic IP amplifier.** A generic assistant notes public access
   in passing. The skill flags the attached EIP as a *stable, DNS-
   portable* public database endpoint — it survives stop/start, making
   the exposure durable across reboots. This raises the operational
   risk and is called out separately in FINDINGS.
