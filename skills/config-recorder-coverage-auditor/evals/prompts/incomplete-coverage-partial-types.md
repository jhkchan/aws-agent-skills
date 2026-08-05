# Eval prompt: incomplete-coverage-partial-types

Audit the following AWS Config setup for coverage and compliance posture.
Emit the standard VERDICT block (AUDIT, REGION, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit reference: incomplete-coverage-partial-types
Account: 111111111111
Region: us-east-1

AWS Config API responses:

describe-configuration-recorders:
  name: default
  roleARN: arn:aws:iam::111111111111:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig
  recordingGroup:
    allSupported: false
    includeGlobalResourceTypes: false
    resourceTypes:
      - AWS::EC2::Instance
      - AWS::EC2::SecurityGroup
      - AWS::EC2::Volume

describe-configuration-recorder-status:
  name: default
  recording: true
  lastStatus: SUCCESS
  lastStartTime: 2026-07-01T00:00:00Z

describe-delivery-channels:
  name: default
  s3BucketName: config-bucket-111111111111
  configSnapshotDeliveryProperties:
    deliveryFrequency: Six_Hours

describe-delivery-channel-status:
  name: default
  lastStatus: SUCCESS
  lastErrorCode: null

describe-config-rules:
  ConfigRules:
    - ConfigRuleName: ec2-volume-inuse-check
      ConfigRuleState: ACTIVE
      Source: {Owner: AWS, SourceIdentifier: AWS::EC2::Volume}

describe-conformance-packs:
  ConformancePacks:
    - ConformancePackName: ec2-best-practices
      ConformancePackId: pack-def456
      DeploymentStatus: CREATE_COMPLETE
