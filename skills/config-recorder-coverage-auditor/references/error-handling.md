# Error Handling (load on demand) — Config Recorder Coverage Auditor

Remediation guidance and API failure recovery moved verbatim from SKILL.md. Loaded on demand.

---

## Remediation guidance (per verdict) (moved from SKILL.md)

### For CONFIG_GAP — no recorder or recorder not recording

1. **No recorder:** create one:
   ```bash
   aws configservice put-configuration-recorder \
     --configuration-recorder name=default,roleARN=arn:aws:iam::<account>:role/service-role/AWSServiceRoleForConfig \
     --recording-group allSupported=true,includeGlobalResourceTypes=true \
     --region <region>
   aws configservice start-configuration-recorder \
     --configuration-recorder-name default --region <region>
   ```

2. **Recorder stopped:** restart it:
   ```bash
   aws configservice start-configuration-recorder \
     --configuration-recorder-name default --region <region>
   ```

3. **Recorder `lastStatus: FAILURE`:** diagnose via `lastErrorMessage`. The
   most common fix is recreating the service-linked role:
   ```bash
   aws iam create-service-linked-role --aws-service-name config.amazonaws.com
   ```
   Then restart the recorder.

### For DELIVERY_GAP — delivery channel broken

1. **No delivery channel:** create one pointing to an S3 bucket with the
   correct bucket policy:
   ```bash
   aws configservice put-delivery-channel \
     --delivery-channel name=default,s3BucketName=<bucket>,configSnapshotDeliveryProperties={deliveryFrequency=Six_Hours} \
     --region <region>
   ```

2. **`NO_SUCH_BUCKET`:** either recreate the bucket or update the delivery
   channel to point to an existing bucket.

3. **`ACCESS_DENIED`:** add the required bucket policy statement granting
   `s3:PutObject` to `config.amazonaws.com`:
   ```json
   {"Effect": "Allow", "Principal": {"Service": "config.amazonaws.com"},
    "Action": "s3:PutObject", "Resource": "arn:aws:s3:::<bucket>/AWSLogs/<account>/Config/*"}
   ```

### For INCOMPLETE_COVERAGE — partial resource-type or region scope

1. **`allSupported: false`:** switch to `allSupported: true` unless there is
   a documented cost-control reason for the narrow scope. Enumerate the
   missing critical types in the finding so the operator can assess impact.

2. **No region with `includeGlobalResourceTypes: true`:** enable it in
   exactly ONE region (typically us-east-1):
   ```bash
   aws configservice put-configuration-recorder \
     --configuration-recorder name=default,roleARN=<role-arn> \
     --recording-group allSupported=true,includeGlobalResourceTypes=true \
     --region us-east-1
   ```
   Disable it in other regions to avoid duplicate IAM recordings.

### For NO_RULES — no compliance evaluation

1. Deploy an AWS-managed conformance pack as a baseline:
   ```bash
   aws configservice put-conformance-pack \
     --conformance-pack-name operational-best-practices \
     --template-s3-uri s3://aws-quickstart/config-conformance-packs/operational-best-practices.yaml \
     --region <region>
   ```

2. Alternatively, deploy individual managed rules:
   ```bash
   aws configservice put-config-rule \
     --config-rule file://rule.json --region <region>
   ```

3. For custom Lambda-backed rules, verify the Lambda function exists and
   has the required permissions (`configservice:PutEvaluations`).

### For OK

1. No remediation required.
2. Recommend periodic re-audit (monthly) to catch configuration drift.
3. Verify conformance pack deployments remain in `CREATE_COMPLETE` or
   `UPDATE_COMPLETE` status.
