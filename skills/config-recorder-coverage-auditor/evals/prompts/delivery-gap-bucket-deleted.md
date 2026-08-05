# Eval prompt: delivery-gap-bucket-deleted

Audit the following AWS Config setup for coverage and compliance posture.
Emit the standard VERDICT block (AUDIT, REGION, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit reference: delivery-gap-bucket-deleted
Account: 111111111111
Region: us-east-1

AWS Config API responses:

describe-configuration-recorders:
  name: default
  roleARN: arn:aws:iam::111111111111:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig
  recordingGroup:
    allSupported: true
    includeGlobalResourceTypes: true
    resourceTypes: []

describe-configuration-recorder-status:
  name: default
  recording: true
  lastStatus: SUCCESS
  lastStartTime: 2026-07-01T00:00:00Z
  lastStopTime: null
  lastErrorMessage: null

describe-delivery-channels:
  name: default
  s3BucketName: config-bucket-deleted-111111111111
  s3KeyPrefix: config/
  snsTopicARN: arn:aws:sns:us-east-1:111111111111:config-notifications
  configSnapshotDeliveryProperties:
    deliveryFrequency: Six_Hours

describe-delivery-channel-status:
  name: default
  lastStatus: FAILURE
  lastErrorCode: NO_SUCH_BUCKET
  lastErrorMessage: "The specified S3 bucket does not exist"
  lastStatusChangeTime: 2026-08-01T12:00:00Z

describe-config-rules:
  ConfigRules:
    - ConfigRuleName: s3-bucket-public-read-prohibited
      ConfigRuleState: ACTIVE
      Source: {Owner: AWS, SourceIdentifier: AWS::S3::Bucket}
    - ConfigRuleName: iam-no-attached-policies
      ConfigRuleState: ACTIVE
      Source: {Owner: AWS, SourceIdentifier: AWS::IAM::User}

describe-conformance-packs:
  ConformancePacks:
    - ConformancePackName: operational-best-practices
      ConformancePackId: pack-abc123
      DeploymentStatus: CREATE_COMPLETE
