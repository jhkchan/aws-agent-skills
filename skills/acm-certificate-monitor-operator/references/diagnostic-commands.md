# Diagnostic Commands — ACM Certificate Monitor Operator

Load-on-demand monitoring and inventory CLI moved verbatim from SKILL.md.

## Step 1 — verify the metric is available (CLI)

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/CertificateManager \
  --metric-name DaysToExpiry \
  --dimensions Name=CertificateArn,Value=arn:aws:acm:us-east-1:123456789012:certificate/abc123-def456 \
  --statistics Average \
  --period 86400 \
  --start-time $(date -u -v-3d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --region us-east-1
```

## Step 2 — warning alarm (< 30 days) CLI

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "acm-cert-warning-<cert-id>" \
  --alarm-description "ACM certificate expires in < 30 days" \
  --namespace AWS/CertificateManager \
  --metric-name DaysToExpiry \
  --dimensions Name=CertificateArn,Value=arn:aws:acm:us-east-1:123456789012:certificate/abc123-def456 \
  --statistic Average \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 30 \
  --comparison-operator LessThanThreshold \
  --treat-missing-data "breaching" \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:cert-warning-notifications" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:cert-warning-notifications" \
  --region us-east-1
```

## Step 2 — critical alarm (< 7 days) CLI

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "acm-cert-critical-<cert-id>" \
  --alarm-description "ACM certificate expires in < 7 days — URGENT" \
  --namespace AWS/CertificateManager \
  --metric-name DaysToExpiry \
  --dimensions Name=CertificateArn,Value=arn:aws:acm:us-east-1:123456789012:certificate/abc123-def456 \
  --statistic Average \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 7 \
  --comparison-operator LessThanThreshold \
  --treat-missing-data "breaching" \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:cert-critical-escalation" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:cert-critical-escalation" \
  --region us-east-1
```

## Step 3 — multi-region certificate inventory loops

```bash
# List certificates across all enabled regions
for REGION in $(aws account get-contact-information \
  --query 'ContactInformation' --output text 2>/dev/null \
  || aws ec2 describe-regions --query 'Regions[*].RegionName' --output text | tr '\t' '\n'); do
  echo "=== Region: $REGION ==="
  aws acm list-certificates --region "$REGION" \
    --output table \
    --query 'CertificateSummaryList[*].{Domain:DomainName,Arn:CertificateArn,Type:Type}'
done
```

**Or for a specific set of regions:**

```bash
for REGION in us-east-1 us-west-2 eu-west-1 ap-southeast-1; do
  echo "=== Region: $REGION ==="
  aws acm list-certificates --region "$REGION" \
    --query 'CertificateSummaryList[*].{Domain:DomainName,Status:Status,Arn:CertificateArn}' \
    --output table
done
```

**Detail per certificate:**

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123-def456 \
  --query 'Certificate.{Domain:DomainName,Status:Status,Type:Type,Issuer:Issuer,NotAfter:NotAfter,NotBefore:NotBefore,KeyAlgorithm:KeyAlgorithm,ValidationMethod:DomainValidationOptions[0].ValidationMethod,RenewalEligibility:RenewalEligibility}' \
  --region us-east-1 --output table
```

## Step 4 — renewal status check (CLI)

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123-def456 \
  --query 'Certificate.{Status:Status,RenewalEligibility:RenewalEligibility,DomainValidation:DomainValidationOptions[*].{Domain:DomainName,ValidationStatus:ValidationStatus,ValidationMethod:ValidationMethod},RenewalSummary:RenewalSummary}' \
  --region us-east-1 --output table
```

## Step 9 — renewal failure detection loop

```bash
for CERT_ARN in $(aws acm list-certificates --certificate-statuses ISSUED \
  --query 'CertificateSummaryList[*].CertificateArn' --output text --region us-east-1); do
  STATUS=$(aws acm describe-certificate --certificate-arn "$CERT_ARN" \
    --query 'Certificate.RenewalSummary.RenewalStatus' --output text --region us-east-1 2>/dev/null)
  [ "$STATUS" = "FAILED" ] && echo "RENEWAL FAILED: $CERT_ARN"
done
```
