# Eval prompt: ok-hardened-cluster

Audit the following EMR cluster configuration for security exposure. Emit the
standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster id: j-OKHARDENED001
Cluster name: ok-hardened-cluster
Cluster metadata (describe-cluster):
  ReleaseLabel: emr-6.10.0
  AutoTerminate: false
  SecurityConfiguration: hardened-config
  ServiceRole: EMR_DefaultRole
  Ec2InstanceAttributes.IamInstanceProfile: EMR_EC2_ScopedRole
  AutoScalingRole: EMR_AutoScaling_DefaultRole
  LogUri: s3://emr-logs-ok/ok-hardened-cluster/
  KerberosAttributes:
    Provider: ClusterDedicatedKdc
    Realm: PROD.INTERNAL
    KdcAdminPassword: (redacted)
  VisibleToAllUsers: false
  InstanceGroups:
    - InstanceGroupType: MASTER, InstanceType: m5.xlarge, RequestedInstanceCount: 3
    - InstanceGroupType: CORE, InstanceType: m5.xlarge, RequestedInstanceCount: 5

SecurityConfiguration contents (describe-security-configuration):
  EncryptionConfiguration:
    AtRestEncryptionConfiguration:
      S3EncryptionConfiguration:
        EncryptionMode: SSE-KMS
        AwsKmsKey: arn:aws:kms:us-east-1:111111111111:key/abc-123
      LocalDiskEncryptionConfiguration:
        EncryptionKeyProviderType: AwsKms
        AwsKmsKey: arn:aws:kms:us-east-1:111111111111:key/def-456
    InTransitEncryptionConfiguration:
      TLSCertificateConfiguration:
        CertificateProviderType: PEM
        S3Object: s3://emr-certs/ok-hardened-cluster/certchain.pem

Block Public Access configuration:
  BlockPublicSecurityGroupRules: true

IAM role summaries:
  ServiceRole (EMR_DefaultRole): AmazonElasticMapReduceRole (AWS managed)
  EC2 instance profile (EMR_EC2_ScopedRole):
    Inline policy "ScopedS3":
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Action: ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
          Resource: ["arn:aws:s3:::emr-input", "arn:aws:s3:::emr-input/*", "arn:aws:s3:::emr-output", "arn:aws:s3:::emr-output/*"]
  AutoScalingRole (EMR_AutoScaling_DefaultRole): AmazonElasticMapReduceAutoScalingRole (AWS managed)
