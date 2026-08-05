# Eval prompt: multi-region-global-types-gap

Audit the following AWS Config setup for coverage and compliance posture
across multiple regions. Emit the standard VERDICT block (AUDIT, REGION,
VERDICT, REASON, FINDINGS, REMEDIATION).

Audit reference: multi-region-global-types-gap
Account: 111111111111
Regions: us-east-1, us-west-2, eu-west-1

AWS Config API responses per region:

=== us-east-1 ===
describe-configuration-recorders:
  name: default
  roleARN: arn:aws:iam::111111111111:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig
  recordingGroup:
    allSupported: true
    includeGlobalResourceTypes: false
    resourceTypes: []

describe-configuration-recorder-status:
  name: default
  recording: true
  lastStatus: SUCCESS

describe-delivery-channels:
  name: default
  s3BucketName: config-bucket-111111111111

describe-delivery-channel-status:
  name: default
  lastStatus: SUCCESS

describe-config-rules:
  ConfigRules:
    - ConfigRuleName: ec2-volume-inuse-check
      ConfigRuleState: ACTIVE

describe-conformance-packs:
  ConformancePacks:
    - ConformancePackName: operational-best-practices
      DeploymentStatus: CREATE_COMPLETE

=== us-west-2 ===
describe-configuration-recorders:
  name: default
  roleARN: arn:aws:iam::111111111111:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig
  recordingGroup:
    allSupported: true
    includeGlobalResourceTypes: false
    resourceTypes: []

describe-configuration-recorder-status:
  name: default
  recording: true
  lastStatus: SUCCESS

describe-delivery-channels:
  name: default
  s3BucketName: config-bucket-111111111111

describe-delivery-channel-status:
  name: default
  lastStatus: SUCCESS

describe-config-rules:
  ConfigRules:
    - ConfigRuleName: s3-bucket-versioning-enabled
      ConfigRuleState: ACTIVE

describe-conformance-packs: (empty)

=== eu-west-1 ===
describe-configuration-recorders:
  name: default
  roleARN: arn:aws:iam::111111111111:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig
  recordingGroup:
    allSupported: true
    includeGlobalResourceTypes: false
    resourceTypes: []

describe-configuration-recorder-status:
  name: default
  recording: true
  lastStatus: SUCCESS

describe-delivery-channels:
  name: default
  s3BucketName: config-bucket-111111111111

describe-delivery-channel-status:
  name: default
  lastStatus: SUCCESS

describe-config-rules:
  ConfigRules:
    - ConfigRuleName: ec2-instance-detailed-monitoring
      ConfigRuleState: ACTIVE

describe-conformance-packs: (empty)

Note: None of the three regions has includeGlobalResourceTypes set to true.
