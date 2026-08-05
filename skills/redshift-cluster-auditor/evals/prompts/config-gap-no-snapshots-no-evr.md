# Eval prompt: config-gap-no-snapshots-no-evr

Audit the following Amazon Redshift cluster configuration for security
exposure and configuration gaps. Emit the standard VERDICT block (CLUSTER,
VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster identifier: config-gap-no-snapshots-no-evr
Cluster ARN: arn:aws:redshift:us-east-1:111111111111:cluster:config-gap-no-snapshots-no-evr

Cluster metadata (describe-clusters):
- ClusterStatus: available
- NumberOfNodes: 2
- NodeType: ra3.xlplus
- PubliclyAccessible: false
- Encrypted: true
- KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/ghi-789
- EnhancedVPCRouting: false
- ClusterParameterGroupName: analytics-pg
- ClusterParameterGroupStatus: in-sync
- AutomatedSnapshotRetentionPeriod: 0
- VpcSecurityGroups: [{VpcSecurityGroupId: sg-0eee99990000, Status: active}]

Parameter group parameters (analytics-pg):
- require_ssl = true (Source: user)
- enable_user_activity_logging = true (Source: user)

Logging status (describe-logging-status):
- LoggingEnabled: true
- BucketName: audit-logs-111111111111
- S3KeyPrefix: redshift/config-gap-no-snapshots-no-evr/

Security group sg-0eee99990000 ingress rules (describe-security-groups):
- tcp 5439-5439 from 10.0.0.0/16
