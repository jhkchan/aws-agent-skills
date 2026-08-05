# Eval prompt: public-cluster-no-encryption

Audit the following Amazon Redshift cluster configuration for security
exposure and configuration gaps. Emit the standard VERDICT block (CLUSTER,
VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster identifier: public-cluster-no-encryption
Cluster ARN: arn:aws:redshift:us-east-1:111111111111:cluster:public-cluster-no-encryption

Cluster metadata (describe-clusters):
- ClusterStatus: available
- NumberOfNodes: 2
- NodeType: ra3.4xlarge
- PubliclyAccessible: true
- Encrypted: false
- KmsKeyId: (none)
- EnhancedVPCRouting: false
- ClusterParameterGroupName: default.redshift-1.0
- ClusterParameterGroupStatus: in-sync
- AutomatedSnapshotRetentionPeriod: 1
- VpcSecurityGroups: [{VpcSecurityGroupId: sg-0aaa11112222, Status: active}]

Parameter group parameters (default.redshift-1.0):
- require_ssl = false (Source: engine-default)
- enable_user_activity_logging = false (Source: engine-default)

Logging status (describe-logging-status):
- LoggingEnabled: false

Security group sg-0aaa11112222 ingress rules (describe-security-groups):
- tcp 5439-5439 from 0.0.0.0/0
