# Eval prompt: audit-logging-disabled-clean

Audit the following Amazon Redshift cluster configuration for security
exposure and configuration gaps. Emit the standard VERDICT block (CLUSTER,
VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster identifier: audit-logging-disabled-clean
Cluster ARN: arn:aws:redshift:us-east-1:111111111111:cluster:audit-logging-disabled-clean

Cluster metadata (describe-clusters):
- ClusterStatus: available
- NumberOfNodes: 2
- NodeType: ra3.xlplus
- PubliclyAccessible: false
- Encrypted: true
- KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/def-456
- EnhancedVPCRouting: true
- ClusterParameterGroupName: analytics-pg
- ClusterParameterGroupStatus: in-sync
- AutomatedSnapshotRetentionPeriod: 7
- VpcSecurityGroups: [{VpcSecurityGroupId: sg-0ddd77778888, Status: active}]

Parameter group parameters (analytics-pg):
- require_ssl = true (Source: user)
- enable_user_activity_logging = true (Source: user)

Logging status (describe-logging-status):
- LoggingEnabled: false

Security group sg-0ddd77778888 ingress rules (describe-security-groups):
- tcp 5439-5439 from 10.0.0.0/16
