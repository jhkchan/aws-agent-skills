# End-to-end usage scenario: athena-workgroup-auditor

A walkthrough showing the skill auditing the `primary` workgroup (the
undeletable AWS-created default), which has every control missing — the
classic open door. Demonstrates the priority-aggregation logic
(NO_ENCRYPTION outranks the compounding NO_LIMITS and CONFIG_GAP
findings) and the assume-breach remediation workflow.

## Input (user prompt)

> We just onboarded a new data lake in us-east-1. Before we let the
> analytics team query it, audit the Athena workgroup setup. Here's the
> `primary` workgroup config:

```json
{
  "Name": "primary",
  "State": "ENABLED",
  "Description": "Auto-created default Athena workgroup.",
  "Configuration": {
    "EnforceWorkGroupConfiguration": false,
    "ResultConfiguration": {
      "OutputLocation": ""
    },
    "BytesScannedCutoffPerQuery": null,
    "PublishCloudWatchMetricsEnabled": false,
    "EngineVersion": {
      "SelectedEngineVersion": "Athena engine version 3"
    }
  }
}
```

> No CloudTrail data events for Athena are configured yet. Named queries:
> none.

## Skill output

```text
WORKGROUP: primary
VERDICT: NO_ENCRYPTION
REASON: Undeletable 'primary' workgroup has EnforceWorkGroupConfiguration
false and no EncryptionConfiguration — every caller inherits plaintext
result writes and can override ResultConfiguration to widen exposure
(Step 3). BytesScannedCutoffPerQuery is also absent, compounding the cost
blast (Step 4).
FINDINGS:
  - [NO_ENCRYPTION] EncryptionConfiguration absent on ResultConfiguration; result objects written to S3 as plaintext (Step 3)
  - [NO_LIMITS] BytesScannedCutoffPerQuery absent; single query can scan unbounded S3 bytes (Step 4)
  - [CONFIG_GAP] EnforceWorkGroupConfiguration false — ResultConfiguration (encryption, OutputLocation) is advisory; only the DSL is binding (Step 2)
  - [CONFIG_GAP] No CloudTrail trail with AWS::Athena data events in us-east-1 — query history falls off the 45-day API cliff (Step 5)
  - [PRIMARY_DEFAULT] Workgroup is 'primary' — undeletable; must be locked down or IAM-quarantined (Step 1)
REMEDIATION:
  1. Set EnforceWorkGroupConfiguration: true — the keystone flip.
     aws athena update-work-group --work-group primary
       --configuration-updates EnforceWorkGroupConfiguration=true
  2. Configure SSE-KMS with a customer-managed key on ResultConfiguration.
     First verify the KMS key policy permits athena.us-east-1.amazonaws.com
     for kms:GenerateDataKey + kms:Decrypt.
     aws athena update-work-group --work-group primary
       --configuration-updates ResultConfigurationUpdates={
         OutputLocation=s3://athena-results-111111111111-us-east-1/primary/,
         EncryptionConfiguration={EncryptionOption=SSE_KMS,
         KmsKey=arn:aws:kms:us-east-1:111111111111:key/primary-cmk}}
  3. Set a binding BytesScannedCutoffPerQuery (1 TB to start; tune down).
     aws athena update-work-group --work-group primary
       --configuration-updates BytesScannedCutoffPerQuery=1099511627776
  4. Enable Athena data events on a CloudTrail trail in us-east-1.
     aws cloudtrail put-event-selectors --trail-name org-trail
       --event-selectors '[{"IncludeManagementEvents":true,"ReadWriteType":"All",
         "DataResources":[{"Type":"AWS::Athena::Workgroup",
         "Values":["arn:aws:athena:us-east-1:111111111111:workgroup/primary"]}]}]'
  5. If primary is not the production workgroup, prefer IAM-quarantine:
     add an explicit Deny on athena:StartQueryExecution for the primary
     workgroup ARN in the analytics team's role policy, then route them
     to a dedicated, fully-governed workgroup instead.
```

## Why the verdict is NO_ENCRYPTION (not CONFIG_GAP or NO_LIMITS)

The skill aggregates multiple findings into a single category verdict
using the priority order NO_ENCRYPTION > NO_LIMITS > CONFIG_GAP > OK.
The `primary` workgroup produces findings in all three non-OK categories:

- The missing EncryptionConfiguration is direct at-rest data exposure
  for every query result object — the highest-severity category.
- The missing DSL is uncapped cost + cross-workgrid quota saturation.
- The enforcement-off + no CloudTrail data events are configuration
  gaps that ENABLE the other findings to persist undetected.

Data exposure outranks cost exposure, which outranks the meta-finding
that the controls are advisory. The skill picks the worst category and
enumerates every contributing finding so the operator sees the full
picture, not just the headline.

## Post-remediation re-audit

After applying steps 1-4 above, the operator re-runs the audit:

```text
WORKGROUP: primary
VERDICT: OK
REASON: EnforceWorkGroupConfiguration is true, SSE-KMS encryption is
configured with a CMK, BytesScannedCutoffPerQuery is set to 1 TB, and
CloudTrail data events are enabled. All dimensions pass (Steps 2-7).
FINDINGS:
  - [OK] EnforceWorkGroupConfiguration true (Step 2)
  - [OK] EncryptionConfiguration SSE_KMS with CMK (Step 3)
  - [OK] BytesScannedCutoffPerQuery 1099511627776 (Step 4)
  - [OK] CloudTrail Athena data events enabled (Step 5)
  - [OK] No named queries — dimension OK by absence (Step 6)
  - [PRIMARY_DEFAULT] Workgroup is 'primary' — undeletable; locked-down posture confirmed (Step 1)
REMEDIATION: None required for the current posture. Recommend periodic
re-audit (workgroup configs drift via UpdateWorkGroup from operators
outside the security team).
```
