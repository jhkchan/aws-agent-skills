# Eval prompt: no-encryption-no-security-config

Audit the following EMR cluster configuration for security exposure. Emit the
standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster id: j-NOENCNOSEC01
Cluster name: no-encryption-no-security-config
Cluster metadata (describe-cluster):
  ReleaseLabel: emr-6.10.0
  AutoTerminate: false
  SecurityConfiguration: (none)
  ServiceRole: EMR_DefaultRole
  Ec2InstanceAttributes.IamInstanceProfile: EMR_EC2_DefaultRole
  AutoScalingRole: EMR_AutoScaling_DefaultRole
  LogUri: s3://emr-logs/no-encryption-no-security-config/
  KerberosAttributes: (none)
  VisibleToAllUsers: true
  InstanceGroups:
    - InstanceGroupType: MASTER, InstanceType: m5.xlarge, RequestedInstanceCount: 1
    - InstanceGroupType: CORE, InstanceType: m5.xlarge, RequestedInstanceCount: 2

SecurityConfiguration contents: NOT PROVIDED (no SecurityConfiguration field on cluster)
