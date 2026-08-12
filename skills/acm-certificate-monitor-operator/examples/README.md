# End-to-End Example: ACM Certificate Monitoring Operations

A walkthrough showing how to use the `acm-certificate-monitor-operator`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are setting up ACM certificate expiry monitoring for 5 issued
certificates in us-east-1 with tiered DaysToExpiry alarms and SNS
notifications. The monitoring needs:

- Account: 123456789012
- Region: us-east-1
- Certificates: 5 issued (ISSUED status)
- Warning alarm: DaysToExpiry < 30 days
- Critical alarm: DaysToExpiry < 7 days
- Warning SNS: arn:aws:sns:us-east-1:123456789012:cert-warning-notifications
- Critical SNS: arn:aws:sns:us-east-1:123456789012:cert-critical-escalation
- Checks: renewal eligibility, DNS validation, CAA records

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:operate-acm-certificates
```

Then paste the requirements.

### Option B: Natural language

```
You: "Set up certificate expiry monitoring for my ACM certs in
      us-east-1. 5 issued certificates. Warning alarm at 30 days,
      critical at 7 days. SNS topics cert-warning-notifications
      and cert-critical-escalation."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "acm certificate monitoring"
```

---

## Step 2 — Skill produces the OPERATION_COMPLETED report

```text
ACM_MONITORING: 123456789012 (us-east-1) — 5 certificates
VERDICT: OPERATION_COMPLETED
FINDINGS:
  [info] All 5 certificates have DaysToExpiry alarms configured (warning + critical)
  [info] All 5 certificates are DNS-validated and attached to supported services
  [info] No CAA conflicts detected
  [info] No renewal failures detected
CHECKLIST:
  [✓] Certificate inventory: 5 certs across us-east-1
  [✓] DaysToExpiry alarms: warning (<30d) and critical (<7d) configured for 5 certs
  [✓] SNS notification: warning → arn:aws:sns:us-east-1:123456789012:cert-warning-notifications, critical → arn:aws:sns:us-east-1:123456789012:cert-critical-escalation
  [✓] Renewal status: 3 ELIGIBLE, 2 INELIGIBLE (not yet in renewal window), 0 FAILED
  [✓] DNS validation: 5 verified, 0 missing records
  [✓] CAA records: 5 OK (amazon.com authorized or no CAA), 0 conflicts
  [✓] Service attachment: 5 attached (3 ALB, 1 CloudFront, 1 API Gateway), 0 unattached
  [✓] Wildcard/SAN coverage: audited (2 wildcard, 3 SAN)
  [✓] PCA private certs: 0 (no private CA in use)
  [✓] Multi-account audit: not applicable (single-account)
VERIFICATION_COMMANDS:
  aws acm list-certificates --certificate-statuses ISSUED --region us-east-1
  aws cloudwatch describe-alarms --alarm-name-prefix acm-cert- --region us-east-1
  aws acm describe-certificate --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 --region us-east-1
  dig example.com CAA +short
```

---

## Step 3 — Monitoring setup commands

```bash
# Step 1: List all ISSUED certificates to get ARNs
CERT_ARNS=$(aws acm list-certificates \
  --certificate-statuses ISSUED \
  --query 'CertificateSummaryList[*].CertificateArn' \
  --output text --region us-east-1)

# Step 2: Create warning + critical alarms for each certificate
for CERT_ARN in $CERT_ARNS; do
  CERT_ID=$(echo "$CERT_ARN" | cut -d'/' -f2)

  # Warning alarm (< 30 days)
  aws cloudwatch put-metric-alarm \
    --alarm-name "acm-cert-warning-${CERT_ID}" \
    --alarm-description "ACM certificate expires in < 30 days" \
    --namespace AWS/CertificateManager \
    --metric-name DaysToExpiry \
    --dimensions Name=CertificateArn,Value="$CERT_ARN" \
    --statistic Average \
    --period 86400 \
    --evaluation-periods 1 \
    --threshold 30 \
    --comparison-operator LessThanThreshold \
    --treat-missing-data "breaching" \
    --alarm-actions "arn:aws:sns:us-east-1:123456789012:cert-warning-notifications" \
    --ok-actions "arn:aws:sns:us-east-1:123456789012:cert-warning-notifications" \
    --region us-east-1

  # Critical alarm (< 7 days)
  aws cloudwatch put-metric-alarm \
    --alarm-name "acm-cert-critical-${CERT_ID}" \
    --alarm-description "ACM certificate expires in < 7 days — URGENT" \
    --namespace AWS/CertificateManager \
    --metric-name DaysToExpiry \
    --dimensions Name=CertificateArn,Value="$CERT_ARN" \
    --statistic Average \
    --period 86400 \
    --evaluation-periods 1 \
    --threshold 7 \
    --comparison-operator LessThanThreshold \
    --treat-missing-data "breaching" \
    --alarm-actions "arn:aws:sns:us-east-1:123456789012:cert-critical-escalation" \
    --ok-actions "arn:aws:sns:us-east-1:123456789012:cert-critical-escalation" \
    --region us-east-1

  echo "Alarms created for: $CERT_ARN"
done

# Step 3: Verify renewal eligibility and DNS validation
for CERT_ARN in $CERT_ARNS; do
  echo "=== $CERT_ARN ==="
  aws acm describe-certificate \
    --certificate-arn "$CERT_ARN" \
    --query 'Certificate.{
      Domain: DomainName,
      Status: Status,
      RenewalEligibility: RenewalEligibility,
      ValidationMethod: DomainValidationOptions[0].ValidationMethod,
      ValidationStatus: DomainValidationOptions[0].ValidationStatus
    }' \
    --output table --region us-east-1
done

# Step 4: Check CAA records for each domain
for CERT_ARN in $CERT_ARNS; do
  DOMAIN=$(aws acm describe-certificate \
    --certificate-arn "$CERT_ARN" \
    --query 'Certificate.DomainName' \
    --output text --region us-east-1)
  # Get the base domain for CAA check
  BASE_DOMAIN=$(echo "$DOMAIN" | sed 's/^[^.]*\.//')
  echo "=== CAA for $BASE_DOMAIN ==="
  dig "$BASE_DOMAIN" CAA +short
done
```

---

## Step 4 — Post-deployment verification

```bash
# Verify all ACM alarms are created
aws cloudwatch describe-alarms \
  --alarm-name-prefix "acm-cert-" \
  --query 'MetricAlarms[*].{Name:AlarmName,State:StateValue,Threshold:Threshold,Actions:AlarmActions}' \
  --output table --region us-east-1

# Verify certificate statuses
aws acm list-certificates \
  --certificate-statuses ISSUED \
  --query 'CertificateSummaryList[*].{Domain:DomainName,ARN:CertificateArn}' \
  --output table --region us-east-1

# Spot-check one certificate's full detail
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --query 'Certificate.{
    Domain: DomainName,
    Status: Status,
    Type: Type,
    NotAfter: NotAfter,
    RenewalEligibility: RenewalEligibility,
    RenewalStatus: RenewalSummary.RenewalStatus,
    ValidationMethod: DomainValidationOptions[0].ValidationMethod
  }' \
  --output table --region us-east-1
```

---

## What the skill catches that a naive monitoring setup misses

| Configuration | Naive setup | Skill output | Why the skill is right |
|---|---|---|---|
| Alarm tiering | Single threshold | Warning (<30d) + critical (<7d) | Single threshold either fires too early or too late; tiering gives graduated response |
| CAA record check | Not checked | Explicit CAA query per domain | CAA conflicts are the #1 silent renewal blocker |
| DNS validation persistence | Not verified | Validation CNAME verified in DNS | Missing validation records cause renewal failure |
| Service attachment | Not checked | Cross-reference with ALB/CloudFront/API Gateway | Unattached certs are NOT auto-renewed |
| Multi-region | Single region | All active regions scanned | ACM is regional; certs in other regions are invisible |
| treat-missing-data | Default (missing) | breaching | If metric stops reporting, alarm should fire not go to INSUFFICIENT_DATA |
| Renewal eligibility | Not checked | ELIGIBLE/INELIGIBLE/FAILED tracked | Proactive detection of renewal issues before expiry alarm |

---

## Related artifacts

- **Skill definition:** `skills/acm-certificate-monitor-operator/SKILL.md`
- **DNS and CAA validation guide:** `skills/acm-certificate-monitor-operator/references/dns-and-caa-validation.md`
- **Multi-account and PCA guide:** `skills/acm-certificate-monitor-operator/references/multi-account-and-pca.md`
- **Slash command:** `commands/aws/operate-acm-certificates.md`
- **Eval suite:** `skills/acm-certificate-monitor-operator/evals/evals.json`
- **Legacy test cases:** `skills/acm-certificate-monitor-operator/eval/test-cases.yaml`
