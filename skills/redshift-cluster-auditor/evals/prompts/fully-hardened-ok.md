# Eval prompt: fully-hardened-ok

Audit the following Amazon Redshift cluster configuration for security
exposure and configuration gaps. Emit the standard VERDICT block (CLUSTER,
VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster identifier: fully-hardened-ok
Cluster ARN: arn:aws:redshift:us-east-1:111111111111:cluster:fully-hardened-ok

Cluster metadata (describe-clusters):
- ClusterStatus: available
- NumberOfNodes: 2
- NodeType: ra3.4xlarge
- PubliclyAccessible: false
- Encrypted: true
- KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-rotated-001
- EnhancedVPCRouting: true
- ClusterParameterGroupName: analytics-pg
- ClusterParameterGroupStatus: in-sync
- AutomatedSnapshotRetentionPeriod: 7
- VpcSecurityGroups: [{VpcSecurityGroupId: sg-0fff22223333, Status: active}]

Parameter group parameters (analytics-pg):
- require_ssl = true (Source: user)
- enable_user_activity_logging = true (Source: user)

Logging status (describe-logging-status):
- LoggingEnabled: true
- BucketName: audit-logs-111111111111
- S3KeyPrefix: redshift/fully-hardened-ok/

Security group sg-0fff22223333 ingress rules (describe-security-groups):
- tcp 5439-5439 from 10.0.0.0/16
