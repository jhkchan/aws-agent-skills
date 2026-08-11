# Eval prompt: create-eds-mgmt-events-sse-kms-ready

Plan the following CloudTrail Lake Event Data Store creation and emit
the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, NOTES).

Operation: create-eds
Name: org-governance-edS
Region: us-east-1
Organization scope: true (org o-abc123def)
Ingestion: CloudTrail management events
Retention: 365 days
KMS: SSE-KMS with key arn:aws:kms:us-east-1:111111111111:key/edS-cmk

```json
{
  "CallerIdentity": {
    "Account": "111111111111",
    "IsManagementAccount": true,
    "OrganizationId": "o-abc123def"
  },
  "OrganizationsAccess": {
    "CloudTrailEnabled": true,
    "ManagementAccountArn": "arn:aws:organizations::111111111111:organization/o-abc123def"
  },
  "KmsKey": {
    "KeyId": "arn:aws:kms:us-east-1:111111111111:key/edS-cmk",
    "KeyState": "Enabled",
    "KeyPolicyGrants": [
      "cloudtrail.amazonaws.com kms:GenerateDataKey",
      "cloudtrail.amazonaws.com kms:Decrypt"
    ]
  },
  "AdvancedEventSelectors": [
    {
      "Name": "management-events",
      "FieldSelectors": [
        {"Field": "eventCategory", "Equals": ["Management"]}
      ]
    }
  ],
  "RetentionPeriodDays": 365,
  "TerminationProtectionEnabled": true
}
```
