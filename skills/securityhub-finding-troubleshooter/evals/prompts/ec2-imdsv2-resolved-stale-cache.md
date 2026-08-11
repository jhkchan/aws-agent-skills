# Eval prompt: ec2-imdsv2-resolved-stale-cache

Diagnose the Security Hub finding below. Walk the standard-driven
decision tree and emit the standard diagnostic block (FINDING, VERDICT,
REASON, LAYER, SEVERITY, STANDARD, EVIDENCE, SUPPRESSION, REMEDIATION).
The FINDING line must reference the test-case id
`ec2-imdsv2-resolved-stale-cache`.

Symptom: Security Hub finding
`arn:aws:securityhub:us-east-1:111111111111:finding/jkl789mno` in
account 111111111111 (us-east-1). Control EC2.8, severity MEDIUM,
Compliance.Status=PASSED, Workflow.Status=RESOLVED. SOC is confused
because the finding is still appearing in the console even though it
shows RESOLVED.

```text
aws securityhub get-findings:
  GeneratorId: "...standards/aws-foundational-security-best-practices/v/1.0.0/EC2.8"
  Resources[0].Id: arn:aws:ec2:us-east-1:111111111111:instance/i-app-1
  Severity.Label: MEDIUM
  Compliance.Status: PASSED
  Workflow.Status: RESOLVED
  UpdatedAt: 2026-08-10T14:32:11Z (8 minutes ago)

aws ec2 describe-instances --instance-ids i-app-1:
  MetadataOptions:
    HttpTokens: required  (the fix is in place)
    HttpPutResponseHopLimit: 1
    HttpEndpoint: enabled

aws configservice get-resource-config-history
  --resource-type AwsEc2Instance --resource-id i-app-1:
  Latest configuration: HttpTokens=required
  Previous configuration: HttpTokens=optional
  Change time: 2026-08-10T14:31:55Z  (8 min ago)

aws configservice describe-config-rules:
  ConfigRuleName: securityhub-ec2-8
  LastEvaluationTime: 2026-08-10T14:33:00Z
  Latest evaluation result for i-app-1: COMPLIANT

SOC ticket notes: instance was remediated at 14:32 UTC; SOC expects
the finding to disappear immediately.
```

Emit the standard diagnostic block.
