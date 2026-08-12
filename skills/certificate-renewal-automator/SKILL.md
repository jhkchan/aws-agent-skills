---
name: certificate-renewal-automator
description: >-
  Designs and implements ACM certificate renewal automation pipelines.
  Detects expiring certificates via CloudWatch alarms on DaysToExpiry,
  wires EventBridge scheduled rules for daily cert scans, deploys Lambda
  functions that request new certificates, validate DNS via Route 53
  CNAME records, update ALB/NLB listeners, rotate API Gateway custom
  domain certificates, and update CloudFront distributions. Covers
  private CA (ACM PCA) lifecycle, cross-account cert sharing via IAM,
  SNI verification, wildcard vs SAN renewal, exported-private-key manual
  renewal, and CloudTrail audit. Emits AUTOMATION_DEPLOYED with a full
  IaC template or REVIEW_REQUIRED with the specific gap.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline workflow design. Live
  deployment uses aws acm describe-certificates, request-certificate,
  get-certificate, aws acm-pca issue-certificate, aws elbv2
  modify-listener, aws apigateway update-domain-name, aws cloudfront
  update-distribution, aws route53 change-resource-record-sets, aws
  events put-rule/put-targets, aws lambda create-function — AWS CLI v2.
keywords:
  - ACM
  - certificate renewal
  - DaysToExpiry
  - CloudWatch alarm
  - EventBridge scheduled rule
  - Lambda renewal
  - DNS validation
  - Route 53 CNAME
  - ACM PCA
  - ALB listener certificate
  - CloudFront distribution
  - API Gateway custom domain
  - SNI verification
  - wildcard certificate
  - SAN certificate
  - CloudTrail audit
tags: [aws-acm, certificate-renewal, tls, security, cloudwatch, eventbridge, lambda, automate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  family: Security
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "AUTOMATION_DEPLOYED | REVIEW_REQUIRED"
  when_to_use: >-
    Building ACM certificate renewal automation, wiring CloudWatch
    alarms for cert expiry, deploying EventBridge + Lambda renewal
    pipelines, managing PCA certificate lifecycles, rotating certs on
    ALB/NLB/CloudFront/API Gateway, or auditing cert API calls.
  activation_triggers:
    - "automate certificate renewal"
    - "ACM expiry alarm"
    - "DaysToExpiry CloudWatch"
    - "certificate rotation Lambda"
    - "DNS validation Route 53"
    - "ACM PCA lifecycle"
    - "ALB listener certificate update"
    - "CloudFront certificate renewal"
    - "API Gateway custom domain cert"
    - "SNI verification"
    - "cross-account certificate sharing"
  invocation_schema: >-
    Input: either (a) a list of ACM certificate ARNs with associated
    services and renewal status, OR (b) a cert renewal automation
    requirement. Output: deterministic RENEWAL block per certificate —
    DETECTION/RENEWAL_FLOW/VALIDATION/NOTIFICATION/AUDIT/VERDICT —
    where VERDICT is AUTOMATION_DEPLOYED or REVIEW_REQUIRED.
---

# Certificate Renewal Automator

## Mindset

**One-line takeaway:** every certificate renewal pipeline is a
five-stage chain — **detect** (CloudWatch DaysToExpiry alarm) →
**trigger** (EventBridge scheduled scan) → **renew** (ACM managed
renewal or Lambda custom flow) → **validate** (DNS CNAME in Route 53)
→ **verify** (SNI check + listener/distribution update confirmation).
A gap in ANY stage produces a silent expiry.

- **ACM managed renewal is NOT universal.** It covers only
  DNS/email-validated certs attached to supported services (ALB, NLB,
  CloudFront, API Gateway). Exported private keys, orphaned certs, and
  PCA-exported certs require manual or custom renewal.
- **PCA-managed certs have a separate lifecycle.** The CA cert itself
  has its own renewal path — two renewal pipelines, not one.
- **DNS validation is the only path to zero-touch renewal.** Email
  validation requires human interaction on every renewal.

## Quick navigation

| You want to... | Go to |
|---|---|
| Detect expiring certs | Step 2 (CloudWatch alarm) |
| Wire daily cert scan | Step 3 (EventBridge) |
| Build Lambda renewal | Step 4 (renewal flow) |
| Automate DNS validation | Step 5 (Route 53 CNAME) |
| Rotate ALB/NLB certs | Step 6 (listener rotation) |
| Rotate CloudFront certs | Step 7 (distribution update) |
| Handle API Gateway domains | Step 8 (API GW rotation) |
| Manage PCA private certs | Step 9 (PCA lifecycle) |
| Share certs cross-account | Step 10 (cross-account IAM) |
| Verify renewal via SNI | Step 11 (SNI check) |
| Audit cert API calls | Step 12 (CloudTrail) |

## Critical rules at a glance

1. **ACM managed renewal fires at 60 days pre-expiry for DNS-validated
   certs attached to a supported service.** If not attached (orphaned),
   ACM does NOT renew. Always verify cert-to-resource association.
2. **Exported private-key certs cannot auto-renew.** ACM has no stored
   private key. Renewal requires re-import. REVIEW_REQUIRED by default.
3. **PCA CA cert renewal is separate from end-cert renewal.** An
   expiring CA breaks ALL certs it issues, regardless of their own
   expiry.
4. **CloudFront certs must be in us-east-1.** Any other region silently
   fails the distribution update.
5. **DNS validation CNAME records must persist for the cert's lifetime.**
   Deleting them after issuance breaks managed renewal silently.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Cert ARN + domain | `acm describe-certificates` | Renewal target |
| Status + validation method | `DomainValidationOptions` | Drives renewal path |
| Associated service | `InUseBy[]` | Managed vs manual |
| DaysToExpiry metric | CloudWatch `AWS/CertificateManager` | Detection |
| Route 53 hosted zone | `route53 list-hosted-zones` | DNS validation |
| PCA CA ARN | `acm-pca list-certificate-authorities` | Private CA lifecycle |

## Process — Renewal pipeline design

### Step 0: Expert knowledge — non-obvious ACM + PCA behaviors

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

### Step 1: Classify the certificate

| Cert class | Validation | Attached | Renewal path |
|---|---|---|---|
| Public ACM | DNS | ALB/NLB/CF/API GW | **Managed** (automatic) |
| Public ACM | DNS | Orphaned | **Custom pipeline** (re-associate or manual) |
| Public ACM | Email | Supported service | **Semi-manual** (email approval) |
| Imported | N/A | Any | **Manual** (re-import) |
| PCA-issued via ACM | DNS | ALB/NLB/API GW | **Custom pipeline** |
| PCA-exported | N/A | On-prem/IoT | **Full manual pipeline** |

Imported certs (private key) are REVIEW_REQUIRED by construction.

### Step 2: CloudWatch alarm on DaysToExpiry

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name acm-cert-expiring-30-days \
  --namespace AWS/CertificateManager \
  --metric-name DaysToExpiry \
  --dimensions Name=CertificateArn,Value=arn:aws:acm:us-east-1:111111111111:certificate/abc-123 \
  --statistic Minimum --period 86400 --threshold 30 \
  --comparison-operator LessThanThreshold --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:cert-expiry-alerts
```

Fleet-wide (omit dimension for minimum across ALL certs):

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name acm-any-cert-expiring-45-days \
  --namespace AWS/CertificateManager --metric-name DaysToExpiry \
  --statistic Minimum --period 86400 --threshold 45 \
  --comparison-operator LessThanThreshold --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:cert-expiry-alerts
```

**Threshold matrix:**

| Threshold | Purpose | Action |
|---|---|---|
| 45 days | Early warning | Notify Slack; verify managed renewal will fire |
| 30 days | Action required | If managed renewal hasn't fired, investigate |
| 14 days | Urgent | Manual renewal path; engage on-call |
| 7 days | Critical | Page on-call; exec escalation |

The metric updates once daily. PENDING_VALIDATION and EXPIRED certs do
NOT emit this metric. A fleet-wide alarm identifies that SOME cert is
expiring but not WHICH — pair with the scan Lambda.

### Step 3: EventBridge daily cert scan

```bash
aws events put-rule \
  --name acm-daily-cert-scan \
  --schedule-expression "rate(1 day)" --state ENABLED

aws events put-targets \
  --rule acm-daily-cert-scan \
  --targets '[{"Id":"cert-scan-lambda","Arn":"arn:aws:lambda:us-east-1:111111111111:function:acm-cert-scan","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:cert-scan-dlq"}}]'
```

The Lambda scans all certs and classifies risk:

```python
import boto3, datetime
acm = boto3.client('acm')
def lambda_handler(event, context):
    certs = acm.list_certificates(CertificateStatuses=['ISSUED'])
    findings = []
    for c in certs['CertificateSummaryList']:
        d = acm.describe_certificate(CertificateArn=c['CertificateArn'])['Certificate']
        days_left = (d['NotAfter'].replace(tzinfo=None) - datetime.datetime.utcnow()).days
        findings.append({
            'domain': d['DomainName'], 'days_to_expiry': days_left,
            'in_use': len(d.get('InUseBy',[])) > 0,
            'renewal_eligibility': d.get('RenewalEligibility','UNKNOWN'),
            'validation': d.get('DomainValidationOptions',[{}])[0].get('ValidationMethod','UNKNOWN')
        })
    findings.sort(key=lambda x: x['days_to_expiry'])
    return {'findings': findings}
```

| Risk | Criteria | Action |
|---|---|---|
| CRITICAL | < 7 days | Page on-call |
| HIGH | < 30 days AND INELIGIBLE | Manual renewal |
| MEDIUM | < 45 days AND orphaned | Re-associate or delete |
| LOW | < 60 days, managed renewal should fire | Verify status |
| OK | >= 60 days AND ELIGIBLE | No action |

### Step 4: Lambda renewal function (custom renewal flow)

For certs requiring custom renewal (orphaned, imported, PCA-issued):

```python
import boto3, time
acm = boto3.client('acm')
route53 = boto3.client('route53')

def renew_certificate(domain_name, hosted_zone_id):
    # Request new cert
    response = acm.request_certificate(
        DomainName=domain_name, ValidationMethod='DNS',
        IdempotencyToken=f'renewal-{int(time.time())}',
        Tags=[{'Key':'ManagedBy','Value':'cert-renewal-automator'}])
    cert_arn = response['CertificateArn']

    # Add DNS validation CNAME
    cert = acm.describe_certificate(CertificateArn=cert_arn)['Certificate']
    for opt in cert.get('DomainValidationOptions', []):
        cname = opt.get('ResourceRecord', {})
        if cname:
            route53.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch={'Changes': [{'Action': 'UPSERT', 'ResourceRecordSet': {
                    'Name': cname['Name'], 'Type': cname['Type'], 'TTL': 300,
                    'ResourceRecords': [{'Value': cname['Value']}]
                }}]})
    # Wait for validation
    waiter = acm.get_waiter('certificate_validated')
    waiter.wait(CertificateArn=cert_arn)
    return cert_arn
```

**Renewal flow decision tree:**

```
DNS-validated + attached to supported service?
├─ Yes → ACM managed renewal. Verify RenewalEligibility = ELIGIBLE.
└─ No → Custom pipeline: request → validate → attach → verify.
    If imported → MANUAL re-import flow.
    If PCA-issued → issue from PCA + validate + attach.
```

### Step 5: DNS validation via Route 53

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:111111111111:certificate/abc-123 \
  --query 'Certificate.DomainValidationOptions[].ResourceRecord'

aws route53 change-resource-record-sets \
  --hosted-zone-id Z1ABCDEF23456 \
  --change-batch '{"Changes":[{"Action":"UPSERT","ResourceRecordSet":{
    "Name":"_abc123.example.com.","Type":"CNAME","TTL":300,
    "ResourceRecords":[{"Value":"_xyz789.acm-validations.aws."}]
  }}]}'
```

**Wildcard and SAN:** A wildcard cert (`*.example.com`) needs ONE CNAME.
A SAN cert needs ONE CNAME PER domain. A SAN combining `example.com` +
`*.example.com` needs TWO CNAMEs.

**Common DNS validation failures:**

| Failure | Fix |
|---|---|
| Validation never completes | Verify CNAME via `dig _abc.example.com CNAME` |
| Renewal fails later | CNAME was deleted — it must persist for the cert's lifetime |
| One SAN domain fails | Add CNAME for each SAN entry |
| CNAME conflict | Remove conflicting TXT/CNAME; ACM needs exclusive use |

### Step 6: ALB/NLB listener certificate rotation

For managed renewal, the listener automatically uses the renewed cert
(ARN unchanged). For custom rotation (new ARN):

```bash
# Single cert
aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:us-east-1:111111111111:listener/app/my-alb/abc/def \
  --certificates CertificateArn=arn:aws:acm:us-east-1:111111111111:certificate/new-abc

# SNI (multiple certs — FIRST is default)
aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:us-east-1:111111111111:listener/app/my-alb/abc/def \
  --certificates \
    CertificateArn=arn:aws:acm:us-east-1:111111111111:certificate/default-abc \
    CertificateArn=arn:aws:acm:us-east-1:111111111111:certificate/sni-www-def \
    CertificateArn=arn:aws:acm:us-east-1:111111111111:certificate/sni-api-ghi
```

**NEVER** replace the entire cert list without preserving SNI order.
Use `add-listener-certificates` to add the new cert, verify, then
`remove-listener-certificates` to remove the old one.

### Step 7: CloudFront distribution certificate update

```bash
aws cloudfront update-distribution \
  --id E1ABCDEF23456 --if-match ETVWXYZ \
  --distribution-config '{"CallerReference":"rotation-001",...,
    "ViewerCertificate":{
      "CloudFrontDefaultCertificate":false,
      "ACMCertificateArn":"arn:aws:acm:us-east-1:111111111111:certificate/new-cert",
      "SSLSupportMethod":"sni-only",
      "MinimumProtocolVersion":"TLSv1.2_2021"}}'
```

**Rules:** Fetch current ETag via `get-distribution` first. `CallerReference`
must be unique per update. Propagation takes 5-60 min — check for
`Status: Deployed`. Cert MUST be in us-east-1.

### Step 8: API Gateway custom domain rotation

```bash
# REST API (v1)
aws apigateway update-domain-name \
  --domain-name api.example.com \
  --patch-operations op=replace,path=/certificateArn,value=arn:aws:acm:us-east-1:111111111111:certificate/new

# HTTP API (v2)
aws apigatewayv2 update-domain-name \
  --domain-name api.example.com --domain-name-id abc123 \
  --domain-name-configurations CertificateArn=arn:aws:acm:us-east-1:111111111111:certificate/new
```

Edge-optimized APIs require us-east-1 certs. Regional APIs require
same-region certs. API mappings are independent of cert rotation.

### Step 9: ACM PCA private certificate lifecycle

```bash
# Check CA validity
aws acm-pca describe-certificate-authority \
  --certificate-authority-arn arn:aws:acm-pca:us-east-1:111111111111:certificate-authority/abc \
  --query 'CertificateAuthority.{Status:Status,NotAfter:NotAfter}'

# Issue new end-certificate
aws acm-pca issue-certificate \
  --certificate-authority-arn arn:aws:acm-pca:us-east-1:111111111111:certificate-authority/abc \
  --csr file://csr.pem --signing-algorithm SHA256WITHRSA \
  --validity Value=365,Type=DAYS --idempotency-token pca-renewal-001
```

**PCA gotchas:** PCA-issued certs via ACM CAN be managed-renewed IF
attached to a supported service and the CA is active. PCA-exported
certs have no managed renewal. The CA itself has a validity period (1-10
years subordinate, up to 25 root) and must be renewed manually.

### Step 10: Cross-account certificate sharing

CloudFront auto-shares us-east-1 certs across the org. ALB/NLB/API
Gateway do NOT support cross-account certs — request separately in each
account.

Consumer IAM role needs:

```json
{"Effect":"Allow","Action":["acm:GetCertificate","acm:DescribeCertificate"],
 "Resource":"arn:aws:acm:us-east-1:111111111111:certificate/*"}
```

### Step 11: SNI verification

```bash
openssl s_client -connect my-alb-123.us-east-1.elb.amazonaws.com:443 \
  -servername www.example.com </dev/null 2>/dev/null | openssl x509 -noout -subject -dates
```

The `notAfter` must reflect the NEW cert. If it shows the old cert's
expiry, propagation is incomplete — wait and retry.

### Step 12: CloudTrail audit

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=acm.amazonaws.com \
  --start-time $(date -v-1d +%Y-%m-%dT%H:%M:%S) --end-time $(date +%Y-%m-%dT%H:%M:%S)

# Anomaly detection — cert deletion or validation resend
aws logs put-metric-filter \
  --log-group-name CloudTrail/DefaultLogGroup --filter-name acm-cert-anomaly \
  --filter-pattern '{$.eventSource = "acm.amazonaws.com" && ($.eventName = "DeleteCertificate" || $.eventName = "ResendValidationEmail")}' \
  --metric-value 1 --metric-namespace SecurityAudit --metric-name CertAPIAnomaly
```

## Output format

```text
RENEWAL: <reference>
CERTIFICATE: <domain-or-arn>
CLASSIFICATION:
  - Validation: DNS | EMAIL | IMPORTED
  - Attached to: ALB | CloudFront | API Gateway | ORPHANED
  - Renewal path: MANAGED | CUSTOM_PIPELINE | MANUAL
DETECTION:
  - CloudWatch alarm: DaysToExpiry < <threshold>
  - EventBridge scan: rate(1 day)
RENEWAL_FLOW:
  - ACM managed: Yes | No
  - Custom Lambda: <function ARN or template reference>
VALIDATION:
  - Method: DNS | EMAIL
  - Route 53 CNAME: <record> -> <target>
NOTIFICATION:
  - SNS topic: <arn>
AUDIT:
  - CloudTrail: cert API tracking
  - SNI verification: openssl per service
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED>
TEMPLATE: <CLI snippet or YAML>
```

### Worked example — AUTOMATION_DEPLOYED

```text
RENEWAL: prod-alb-cert-renewal
CERTIFICATE: www.example.com (arn:aws:acm:us-east-1:111111111111:certificate/abc-123)
CLASSIFICATION:
  - Validation: DNS
  - Attached to: ALB
  - Renewal path: MANAGED (ACM auto-renewal for DNS-validated cert on supported service)
DETECTION:
  - CloudWatch alarm: DaysToExpiry < 45 with SNS action
  - EventBridge scan: rate(1 day) Lambda cert-scan
RENEWAL_FLOW:
  - ACM managed: Yes (RenewalEligibility: ELIGIBLE)
  - Custom Lambda: Not required
VALIDATION:
  - Method: DNS
  - Route 53 CNAME: _abc123.www.example.com -> _xyz789.acm-validations.aws.
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:cert-expiry-alerts
AUDIT:
  - CloudTrail: acm.amazonaws.com event tracking
  - SNI verification: openssl s_client -servername www.example.com
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws cloudwatch put-metric-alarm --alarm-name acm-www-expiring-45 --namespace AWS/CertificateManager --metric-name DaysToExpiry --dimensions Name=CertificateArn,Value=arn:aws:acm:us-east-1:111111111111:certificate/abc-123 --statistic Minimum --period 86400 --threshold 45 --comparison-operator LessThanThreshold --evaluation-periods 1 --alarm-actions arn:aws:sns:us-east-1:111111111111:cert-expiry-alerts
```

### Worked example — REVIEW_REQUIRED

```text
RENEWAL: orphaned-imported-cert
CERTIFICATE: api.internal.example.com (arn:aws:acm:us-east-1:111111111111:certificate/def-456)
CLASSIFICATION:
  - Validation: IMPORTED (private key from external CA)
  - Attached to: ORPHANED (InUseBy: [])
  - Renewal path: MANUAL (ACM cannot renew imported certs)
DETECTION:
  - CloudWatch alarm: DaysToExpiry < 30 (fires but no auto-remediation)
  - EventBridge scan: flagged as HIGH risk
RENEWAL_FLOW:
  - ACM managed: No (INELIGIBLE)
  - Custom Lambda: Requires external CA renewal + re-import
VALIDATION:
  - Method: IMPORTED (N/A)
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:cert-expiry-alerts
AUDIT:
  - CloudTrail: acm.amazonaws.com event tracking
VERDICT: REVIEW_REQUIRED
GAP: Imported private-key certificate with no managed renewal path. Required: (1) Renew at external CA; (2) export new cert+key+chain; (3) import via acm import-certificate; (4) re-associate to target. Migrate to DNS-validated ACM cert or PCA-issued cert for managed renewal.
TEMPLATE: (manual import flow — see references/imported-cert-manual-renewal.md)
```

## Anti-Patterns — NEVER do these

- NEVER assume ACM managed renewal covers all certificates. It covers
  ONLY DNS/email-validated certs attached to supported services. Always
  check `RenewalEligibility`.

- NEVER delete DNS validation CNAMEs after issuance. They must persist
  for the cert's lifetime for ACM to re-validate during renewal.

- NEVER request a new certificate without checking for existing ones.
  `request-certificate` creates duplicates. Use `list-certificates` first.

- NEVER put a CloudFront cert outside us-east-1. It silently fails.

- NEVER update an ALB listener cert list without preserving SNI order.
  `modify-listener --certificates` REPLACES the entire list.

- NEVER use email validation for new certificates. It requires human
  action on every renewal. Use DNS validation.

- NEVER forget PCA CA expiry. An expired CA breaks all certs it issued
  even if end-certs haven't reached their own expiry. Check CA
  `NotAfter` 90+ days in advance.

- NEVER update a CloudFront distribution with a stale ETag. It fails
  silently. Always `get-distribution` for the current ETag first.

- NEVER omit the DLQ on the EventBridge cert-scan target. Without a
  DLQ, failed scans are silently dropped.

- NEVER skip SNI verification after rotation. The config may show the
  new cert but the TLS handshake may still serve the old cert during
  propagation.

- NEVER share certs cross-account for ALB/NLB. They require same-account
  certs. Request separately in each account.

- NEVER rotate all certs simultaneously. Rotate one, verify, then
  proceed. A batch failure leaves the fleet inconsistent.

- NEVER omit CloudTrail auditing. A compromised credential can
  `delete-certificate` to disrupt renewal.

## Pre-flight safety checks

- **CONFIRMATION GATE** before any state-changing operation:
  `CONFIRM: About to <action> for certificate <domain> in account
  <account>. Proceed? (yes/no)`

- **Back up configs:** Save listener/distribution config before
  modifying.

- **Before production rotation:** verify new cert status is `issued`:
  `aws acm describe-certificate --certificate-arn <new> --query 'Certificate.Status'`

- **Before deleting old cert:** verify `InUseBy` is `[]`.

- **For PCA rotation:** verify CA is `ACTIVE`.

## Appendix A — Renewal eligibility matrix

| Cert type | Validation | Attached | Managed renewal | Action |
|---|---|---|---|---|
| Public ACM | DNS | ALB/NLB/CF/API GW | Yes | Verify ELIGIBLE |
| Public ACM | DNS | Orphaned | No | Re-associate or custom |
| Public ACM | Email | Supported | Yes (email approval) | Migrate to DNS |
| Imported | N/A | Any | No | Manual re-import |
| PCA via ACM | DNS | ALB/NLB/API GW | Yes (CA active) | Verify CA health |
| PCA-exported | N/A | On-prem/IoT | No | Manual issue+export |

See **references/acm-renewal-paths.md** for full CLI references.

## Appendix B — Decision tree

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

## Appendix C — CloudFormation skeleton

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

## Domain

AWS CloudOps / Security Automation — TLS certificate lifecycle.

## AWS documentation

- **ACM Managed Renewal** — https://docs.aws.amazon.com/acm/latest/userguide/managed-renewal.html
- **ACM DNS Validation** — https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html
- **AWS Private CA** — https://docs.aws.amazon.com/acm-pca/latest/userguide/PcaWelcome.html
- **CloudFront Viewer Certificates** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-alternate-domain-names.html
- **ALB SNI** — https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-https-listeners.html
