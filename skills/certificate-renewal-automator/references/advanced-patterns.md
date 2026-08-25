# certificate-renewal-automator — advanced patterns (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## Step 0: Expert knowledge — non-obvious ACM + PCA behaviors

- **Managed renewal attempts begin 60 days before expiry and repeat
  daily.** `RenewalEligibility: ELIGIBLE` means ACM will attempt
  managed renewal. `INELIGIBLE` means it will NOT — investigate.

- **Email-validated certs require human action on every renewal.** ACM
  sends approval emails 45 days pre-expiry. If no one clicks the link,
  the cert expires. Migrate to DNS validation.

- **`InUseBy` is the source of truth for association.** Empty
  `InUseBy` = orphaned. ACM does NOT renew orphaned certs.

- **Wildcard certs renew as one unit.** `*.example.com` covers all
  first-level subdomains — no per-subdomain renewal. SAN certs renew
  ALL domains as a unit; one failed validation blocks the entire renewal.

- **PCA end-certs expire on their own schedule, not the CA's.** But if
  the CA expires before the end-cert, the end-cert becomes un-verifiable.

- **CloudFront cert updates take 5-60 minutes to propagate.**
  `update-distribution` returns immediately; SNI verification across
  edge locations is required before declaring rotation complete.

- **ALB supports SNI with multiple certs per listener.** The first cert
  is the default; subsequent certs are SNI-matched. A renewal that
  replaces the default without preserving SNI certs breaks non-default
  domains.

- **Cross-account cert references work only for CloudFront (us-east-1).**
  ALB/NLB/API Gateway require the cert in the same account and region.

- **`request-certificate` is NOT idempotent.** Calling it twice for the
  same domain creates duplicate certs. Always check `list-certificates`
  first.

## Fleet-wide DaysToExpiry alarm (secondary detection example)

Fleet-wide (omit dimension for minimum across ALL certs):

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name acm-any-cert-expiring-45-days \
  --namespace AWS/CertificateManager --metric-name DaysToExpiry \
  --statistic Minimum --period 86400 --threshold 45 \
  --comparison-operator LessThanThreshold --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:cert-expiry-alerts
```

## Appendix B — Decision tree (renewal path classification)

```
DNS-validated + attached to supported service?
├─ Yes → RenewalEligibility = ELIGIBLE?
│       ├─ Yes → AUTOMATION_DEPLOYED (managed renewal)
│       └─ No  → REVIEW_REQUIRED (CNAME deleted? SAN mismatch?)
├─ No → Imported cert?
│       ├─ Yes → REVIEW_REQUIRED (manual re-import)
│       └─ No  → PCA-issued?
│               ├─ CA active → Custom pipeline
│               └─ CA expired → REVIEW_REQUIRED (renew CA first)
```

## Appendix C — CloudFormation skeleton (renewal automation pipeline)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'ACM Certificate Renewal Automation Pipeline'
Resources:
  CertExpiryTopic:
    Type: AWS::SNS::Topic
    Properties: {TopicName: cert-expiry-alerts}
  CertScanRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement: [{Effect: Allow, Principal: {Service: lambda.amazonaws.com}, Action: sts:AssumeRole}]
      ManagedPolicyArns: [arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole]
      Policies:
        - PolicyName: ACMAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - {Effect: Allow, Action: [acm:DescribeCertificate, acm:ListCertificates, acm:RequestCertificate], Resource: '*'}
              - {Effect: Allow, Action: [route53:ChangeResourceRecordSets, route53:ListHostedZones], Resource: '*'}
              - {Effect: Allow, Action: [sns:Publish], Resource: !Ref CertExpiryTopic}
  CertScanFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: acm-cert-scan
      Runtime: python3.12
      Handler: index.lambda_handler
      Role: !GetAtt CertScanRole.Arn
      Timeout: 120
      Environment: {Variables: {SNS_TOPIC_ARN: !Ref CertExpiryTopic, DAYS_THRESHOLD: '45'}}
      Code: {ZipFile: 'import boto3,os,datetime\nacm=boto3.client("acm")\nsns=boto3.client("sns")\ndef lambda_handler(e,c):\n  t=int(os.environ["DAYS_THRESHOLD"])\n  for x in acm.list_certificates(CertificateStatuses=["ISSUED"])["CertificateSummaryList"]:\n    d=acm.describe_certificate(CertificateArn=x["CertificateArn"])["Certificate"]\n    dl=(d["NotAfter"].replace(tzinfo=None)-datetime.datetime.utcnow()).days\n    if dl<t: sns.publish(TopicArn=os.environ["SNS_TOPIC_ARN"],Subject="Cert Expiry",Message=f\'{d["DomainName"]}: {dl} days\')'}
  DailyScanRule:
    Type: AWS::Events::Rule
    Properties:
      ScheduleExpression: rate(1 day)
      State: ENABLED
      Targets: [{Id: cert-scan, Arn: !GetAtt CertScanFunction.Arn, DeadLetterConfig: {Arn: !GetAtt CertScanDLQ.Arn}}]
  CertScanDLQ:
    Type: AWS::SQS::Queue
    Properties: {QueueName: cert-scan-dlq}
  ScanPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref CertScanFunction
      Action: lambda:InvokeFunction
      Principal: events.amazonaws.com
      SourceArn: !GetAtt DailyScanRule.Arn
  FleetAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: acm-any-cert-expiring-45-days
      Namespace: AWS/CertificateManager
      MetricName: DaysToExpiry
      Statistic: Minimum
      Period: 86400
      EvaluationPeriods: 1
      Threshold: 45
      ComparisonOperator: LessThanThreshold
      AlarmActions: [!Ref CertExpiryTopic]
```

## Recent AWS features (2024-2026)

- **RenewalEligibility visibility (2024):** `describe-certificate` now
  clearly shows `ELIGIBLE` vs `INELIGIBLE` for managed renewal. Use as
  the primary renewal-health signal.
- **AWS Private CA throughput mode (2024-2025):** Higher cert-issuance
  rates for large-scale private cert pipelines.
- **CloudFront TLS 1.3 (2024):** Update `MinimumProtocolVersion` to
  `TLSv1.2_2021` or later during cert rotation.
- **EventBridge Scheduler (2024-2025):** Prefer over classic scheduled
  rules for new cert-scan deployments — per-target retry policies and
  flexible cron.

## Expert heuristic: renewal coverage gap

The most dangerous expiry is the one you don't know about. ACM managed
renewal creates false security — operators assume "ACM handles it." The
gap is threefold:

1. **Imported certs** are invisible to managed renewal.
2. **Orphaned certs** lose managed renewal when their resource is deleted.
3. **PCA CA expiry** cascades to all end-certs.

**The rule:** ALWAYS deploy a daily cert-scan Lambda with a CloudWatch
alarm at 45 days, regardless of managed renewal. The scan catches all
three gaps. Managed renewal is primary; the scan is the verification layer.

**Verification protocol:**

| Layer | Mechanism | Frequency |
|---|---|---|
| Primary | ACM managed renewal | Automatic (60 days pre-expiry) |
| Secondary | Daily EventBridge Lambda scan | Every 24 hours |
| Tertiary | CloudWatch DaysToExpiry alarm | Continuous |
| Audit | CloudTrail cert API review | Weekly |
| PCA-specific | CA NotAfter + end-cert matrix | Weekly |
