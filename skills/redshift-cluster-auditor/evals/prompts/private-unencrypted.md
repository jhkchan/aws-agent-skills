# Eval prompt: private-unencrypted

Audit the following Amazon Redshift cluster configuration for security
exposure and configuration gaps. Emit the standard VERDICT block (CLUSTER,
VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster identifier: private-unencrypted
Cluster ARN: arn:aws:redshift:us-east-1:111111111111:cluster:private-unencrypted

Cluster metadata (describe-clusters):
- ClusterStatus: available
- NumberOfNodes: 2
- NodeType: ra3.xlplus
- PubliclyAccessible: false
- Encrypted: false
- KmsKeyId: (none)
- EnhancedVPCRouting: true
- ClusterParameterGroupName: analytics-pg
- ClusterParameterGroupStatus: in-sync
- AutomatedSnapshotRetentionPeriod: 7
- VpcSecurityGroups: [{VpcSecurityGroupId: sg-0bbb33334444, Status: active}]

Parameter group parameters (analytics-pg):
- require_ssl = true (Source: user)
- enable_user_activity_logging = true (Source: user)

Logging status (describe-logging-status):
- LoggingEnabled: true
- BucketName: audit-logs-111111111111
- S3KeyPrefix: redshift/private-unencrypted/

Security group sg-0bbb33334444 ingress rules (describe-security-groups):
- tcp 5439-5439 from 10.0.0.0/16
