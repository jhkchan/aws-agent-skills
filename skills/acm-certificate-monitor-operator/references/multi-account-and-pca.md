# Multi-Account Audit and ACM PCA — ACM Certificate Monitor Operator

Deep reference on multi-account certificate auditing via AWS
Organizations, assume-role patterns for cross-account ACM access,
ACM Private Certificate Authority (PCA) monitoring, private
certificate lifecycle, and certificate-to-resource mapping across
services. Loaded on demand by the skill — kept out of the main
SKILL.md body so the monitoring procedure stays scannable.

## Multi-account audit architecture

### Monitoring account model

```text
  Audit Account (111111111111)
  ┌──────────────────────────────┐
  │  Audit orchestrator          │
  │  (Lambda / CLI / Script)     │
  │                              │
  │  Assumes role in each member │
  │  account to scan certificates│
  └──────┬───────┬───────┬───────┘
         │       │       │
    assume│  assume│  assume│
    role  │  role  │  role  │
         │       │       │
  ┌──────▼──┐ ┌──▼────┐ ┌▼──────┐
  │ Prod    │ │ Stag  │ │ Dev   │
  │ Account │ │ Acct  │ │ Acct  │
  │ 222222  │ │ 333333│ │ 444444│
  │         │ │       │ │       │
  │ ACMMLab │ │ ACMML │ │ ACMML │
  │ Role    │ │ Role  │ │ Role  │
  └─────────┘ └───────┘ └───────┘
```

### Member account IAM role for monitoring

Each member account needs a role that the audit account can assume,
with read-only ACM and CloudWatch permissions.

**Trust policy (member account role):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111111111111:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Permission policy (member account role):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "acm:ListCertificates",
        "acm:DescribeCertificate",
        "acm:GetCertificate",
        "cloudwatch:DescribeAlarms",
        "cloudwatch:GetMetricStatistics",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeListeners",
        "cloudfront:ListDistributions",
        "apigateway:GetDomainNames"
      ],
      "Resource": "*"
    }
  ]
}
```

### Create the monitoring role via CloudFormation StackSet

For organizations with many accounts, deploy the monitoring role via
CloudFormation StackSet across the Organization:

```bash
aws cloudformation create-stack-set \
  --stack-set-name "ACMMonitoringRole" \
  --template-body file:///tmp/acm-monitoring-role.yaml \
  --permission-model SERVICE_MANAGED \
  --capabilities CAPABILITY_NAMED_IAM \
  --auto-deployment Enabled=true,RetainStacksOnAccountDeletion=false

aws cloudformation create-stack-instances \
  --stack-set-name "ACMMonitoringRole" \
  --deployment-targets OrganizationalUnitIds="ou-abc123-xxxxx" \
  --regions us-east-1
```

### Multi-account audit script

```bash
#!/bin/bash
# ACM multi-account certificate audit
AUDIT_ACCOUNT="111111111111"
ROLE_NAME="ACMMonitoringRole"
REGIONS="us-east-1 us-west-2 eu-west-1 ap-southeast-1"

# Get all active accounts in the Organization
ACCOUNTS=$(aws organizations list-accounts \
  --query 'Accounts[?Status==`ACTIVE`].Id' \
  --output text)

for ACCT_ID in $ACCOUNTS; do
  echo "============================================"
  echo "Account: $ACCT_ID"
  echo "============================================"

  # Skip the audit account itself (already have access)
  if [ "$ACCT_ID" = "$AUDIT_ACCOUNT" ]; then
    continue
  fi

  # Assume the monitoring role
  CREDS=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$ACCT_ID:role/$ROLE_NAME" \
    --role-session-name "acm-audit-$(date +%s)" \
    --query 'Credentials' --output json 2>/dev/null)

  if [ $? -ne 0 ]; then
    echo "  [ERROR] Cannot assume role in account $ACCT_ID"
    continue
  fi

  export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.AccessKeyId')
  export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.SecretAccessKey')
  export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.SessionToken')

  for REGION in $REGIONS; do
    echo "  Region: $REGION"

    # List all certificates
    CERTS=$(aws acm list-certificates \
      --region "$REGION" \
      --query 'CertificateSummaryList[*].CertificateArn' \
      --output text 2>/dev/null)

    for CERT_ARN in $CERTS; do
      aws acm describe-certificate \
        --certificate-arn "$CERT_ARN" \
        --region "$REGION" \
        --query 'Certificate.{
          Domain: DomainName,
          Status: Status,
          Type: Type,
          RenewalEligibility: RenewalEligibility,
          NotAfter: NotAfter
        }' \
        --output table 2>/dev/null
    done
  done

  unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
done
```

### Aggregate findings report

The audit should produce a summary report with:

| Finding | Severity | Description |
|---|---|---|
| Expiring soon (<30 days) | Warning | Certificate approaching expiry |
| Expiring soon (<7 days) | Critical | Certificate in critical window |
| Renewal FAILED | Critical | ACM renewal attempt failed |
| Unattached certificate | Warning | Not attached to a supported service |
| PENDING_VALIDATION | Info | Certificate not yet validated |
| EXPIRED | Critical | Certificate already expired |
| CAA conflict suspected | Critical | Renewal failing, CAA likely cause |

## ACM PCA (Private Certificate Authority) monitoring

### Private CA lifecycle

```text
ACM PCA Private CA lifecycle:
  1. Create private CA (acm-pca:create-certificate-authority)
     → CA certificate issued (10-year validity by default)
     → Status: ACTIVE

  2. Issue private certificates via ACM (acm:request-certificate)
     → Certificate signed by private CA
     → Status: ISSUED
     → Validity: configurable (default 1 year for private certs)

  3. Private cert renewal
     → ACM does NOT auto-renew private certificates
     → Must manually re-request or use API/Lambda automation
     → Short-lived certs (hours/days) need frequent renewal automation

  4. CA certificate expiry
     → When CA cert expires, all certs issued by it become invalid
     → Must renew the CA cert before it expires (10-year window)
```

### Monitor PCA CA certificate health

```bash
# List all private CAs
aws acm-pca list-certificate-authorities \
  --query 'CertificateAuthorities[*].{
    ARN: Arn,
    Status: Status,
    Type: Type,
    CommonName: CertificateAuthorityConfiguration.Subject.CommonName,
    NotBefore: NotBefore,
    NotAfter: NotAfter
  }' \
  --output table --region us-east-1

# Get detailed CA status
aws acm-pca describe-certificate-authority \
  --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/abc123 \
  --query 'CertificateAuthority.{
    Status: Status,
    Type: Type,
    NotBefore: NotBefore,
    NotAfter: NotAfter,
    KeyStorage: KeyStorageSecurityStandard,
    Revocation: RevocationConfiguration
  }' \
  --output table --region us-east-1
```

### Create PCA CA expiry alarm

PCA CA certificates do not have a built-in DaysToExpiry metric. Use
EventBridge scheduled rules + Lambda to compute and publish a custom
metric:

```python
import boto3
import datetime
from datetime import timezone

acm_pca = boto3.client('acm-pca')
cloudwatch = boto3.client('cloudwatch')

def lambda_handler(event, context):
    cas = acm_pca.list_certificate_authorities()

    for ca in cas['CertificateAuthorities']:
        ca_arn = ca['Arn']
        not_after = ca['NotAfter']  # ISO 8601 timestamp

        # Parse the expiry date
        expiry = datetime.datetime.strptime(
            not_after.replace('T', ' ').replace('Z', ''),
            '%Y-%m-%d %H:%M:%S'
        ).replace(tzinfo=timezone.utc)

        days_remaining = (expiry - datetime.datetime.now(timezone.utc)).days

        # Publish custom metric
        cloudwatch.put_metric_data(
            Namespace='ACM/PCA',
            MetricData=[{
                'MetricName': 'CADaysToExpiry',
                'Dimensions': [{'Name': 'CAArn', 'Value': ca_arn}],
                'Value': days_remaining,
                'Unit': 'Count'
            }]
        )

        print(f"CA {ca_arn}: {days_remaining} days remaining")

    return {'statusCode': 200}
```

```bash
# Create alarm on the custom PCA CA metric
aws cloudwatch put-metric-alarm \
  --alarm-name "pca-ca-expiry-warning" \
  --namespace ACM/PCA \
  --metric-name CADaysToExpiry \
  --statistic Average \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 365 \
  --comparison-operator LessThanThreshold \
  --treat-missing-data "breaching" \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:pca-alerts" \
  --region us-east-1
```

### Private certificate renewal automation

Since ACM does NOT auto-renew private certificates, set up renewal
automation:

```python
import boto3
import datetime
from datetime import timezone

acm = boto3.client('acm')

def lambda_handler(event, context):
    # List private certificates (issued by PCA)
    certs = acm.list_certificates(
        CertificateStatuses=['ISSUED']
    )

    for cert in certs['CertificateSummaryList']:
        cert_detail = acm.describe_certificate(
            CertificateArn=cert['CertificateArn']
        )

        # Check if it's a private cert
        if cert_detail['Certificate'].get('Type') != 'AMAZON_ISSUED':
            # Private cert — check expiry
            not_after = cert_detail['Certificate']['NotAfter']
            expiry = datetime.datetime.strptime(
                not_after.replace('T', ' ').replace('Z', ''),
                '%Y-%m-%d %H:%M:%S'
            ).replace(tzinfo=timezone.utc)

            days_remaining = (expiry - datetime.datetime.now(timezone.utc)).days

            if days_remaining < 30:
                # Re-request the certificate
                print(f"Renewing private cert: {cert['CertificateArn']}")
                acm.request_certificate(
                    DomainName=cert_detail['Certificate']['DomainName'],
                    CertificateAuthorityArn=cert_detail['Certificate'].get(
                        'CertificateAuthorityArn'
                    ),
                    ValidityNotAfter=datetime.datetime.now(timezone.utc) +
                        datetime.timedelta(days=365)
                )

    return {'statusCode': 200}
```

## Certificate-to-resource mapping across services

### ALB / NLB

```bash
# Find all certificates attached to ALBs/NLBs
aws elbv2 describe-listeners \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/prod-alb/1234567890 \
  --query 'Listeners[*].{
    Protocol: Protocol,
    Port: Port,
    Certs: Certificates[*].CertificateArn
  }' \
  --output table --region us-east-1
```

### CloudFront

```bash
# CloudFront certs must be in us-east-1
aws cloudfront list-distributions \
  --query 'DistributionList.Items[*].{
    Domain: DomainName,
    CertARN: ViewerCertificate.ACMCertificateArn,
    CertName: ViewerCertificate.Certificate,
    MinVersion: ViewerCertificate.MinimumProtocolVersion
  }' \
  --output table --region us-east-1
```

### API Gateway (REST API custom domains)

```bash
aws apigateway get-domain-names \
  --query 'items[*].{
    Domain: domainName,
    CertARN: certificateArn,
    CertName: certificateName,
    Endpoint: endpointConfiguration.types[0]
  }' \
  --output table --region us-east-1
```

### API Gateway (HTTP API custom domains)

```bash
aws apigatewayv2 get-domain-names \
  --query 'Items[*].{
    Domain: DomainName,
    CertARN: DomainNameConfigurations[0].CertificateArn,
    SecurityPolicy: DomainNameConfigurations[0].SecurityPolicy
  }' \
  --output table --region us-east-1
```

### AppSync

```bash
aws appsync list-graphql-apis \
  --query 'graphqlApis[*].{
    Name: name,
    Domain: uris.GRAPHQL,
    CertARN: lambdaAuthorizerConfig.authorizerUri
  }' \
  --output table --region us-east-1
```

### Cross-reference: find unattached certificates

```bash
#!/bin/bash
# Find ACM certificates not attached to any supported service

REGION="us-east-1"
ACCOUNT="123456789012"

# Get all ISSUED certificates
ALL_CERTS=$(aws acm list-certificates \
  --certificate-statuses ISSUED \
  --query 'CertificateSummaryList[*].CertificateArn' \
  --output text --region $REGION)

# Get certificates attached to ALBs
ALB_CERTS=$(aws elbv2 describe-listeners \
  --query 'Listeners[*].Certificates[*].CertificateArn' \
  --output text --region $REGION 2>/dev/null | tr '\t' '\n')

# Get certificates attached to CloudFront
CF_CERTS=$(aws cloudfront list-distributions \
  --query 'DistributionList.Items[*].ViewerCertificate.ACMCertificateArn' \
  --output text --region $REGION 2>/dev/null | tr '\t' '\n')

# Get certificates attached to API Gateway
APIGW_CERTS=$(aws apigateway get-domain-names \
  --query 'items[*].certificateArn' \
  --output text --region $REGION 2>/dev/null | tr '\t' '\n')

ATTACHED=$(echo "$ALB_CERTS $CF_CERTS $APIGW_CERTS" | sort -u)

echo "=== Unattached certificates ==="
for CERT in $ALL_CERTS; do
  if ! echo "$ATTACHED" | grep -q "$CERT"; then
    DOMAIN=$(aws acm describe-certificate \
      --certificate-arn "$CERT" \
      --query 'Certificate.DomainName' \
      --output text --region $REGION)
    echo "  UNATTACHED: $DOMAIN ($CERT)"
  fi
done
```

## Terraform examples

### DaysToExpiry alarm for each certificate

```hcl
# Get all issued certificates
data "aws_acm_certificates" "issued" {
  statuses = ["ISSUED"]
}

# Create warning + critical alarms for each
resource "aws_cloudwatch_metric_alarm" "cert_warning" {
  for_each = toset(data.aws_acm_certificates.issued.arns)

  alarm_name          = "acm-cert-warning-${element(split("/", each.value), 1)}"
  alarm_description   = "ACM certificate expires in < 30 days"
  namespace           = "AWS/CertificateManager"
  metric_name         = "DaysToExpiry"
  dimensions = {
    CertificateArn = each.value
  }
  statistic           = "Average"
  period              = 86400
  evaluation_periods  = 1
  threshold           = 30
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"

  alarm_actions = [aws_sns_topic.cert_warning.arn]
  ok_actions    = [aws_sns_topic.cert_warning.arn]
}

resource "aws_cloudwatch_metric_alarm" "cert_critical" {
  for_each = toset(data.aws_acm_certificates.issued.arns)

  alarm_name          = "acm-cert-critical-${element(split("/", each.value), 1)}"
  alarm_description   = "ACM certificate expires in < 7 days — URGENT"
  namespace           = "AWS/CertificateManager"
  metric_name         = "DaysToExpiry"
  dimensions = {
    CertificateArn = each.value
  }
  statistic           = "Average"
  period              = 86400
  evaluation_periods  = 1
  threshold           = 7
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"

  alarm_actions = [aws_sns_topic.cert_critical.arn]
  ok_actions    = [aws_sns_topic.cert_critical.arn]
}
```

## Step 7 — certificate-to-load-balancer mapping (CLI)

**Find certificates attached to ALBs/NLBs:**

```bash
# List listeners with cert details for each LB
for LB_ARN in $(aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[*].LoadBalancerArn' --output text --region us-east-1); do
  aws elbv2 describe-listeners --load-balancer-arn "$LB_ARN" \
    --query 'Listeners[*].{Protocol:Protocol,Certs:Certificates[*].CertificateArn}' \
    --output table --region us-east-1
done
```

**CloudFront and API Gateway:** CloudFront cert ARNs are in
`aws cloudfront list-distributions --query 'DistributionList.Items[*].ViewerCertificate.ACMCertificateArn'`.
API Gateway custom domain certs are in
`aws apigateway get-domain-names --query 'items[*].certificateArn'`.

**Identify unattached certificates (at risk of not auto-renewing):**

```bash
# Cross-reference all ISSUED certs with ALB/NLB/CloudFront/API GW attached certs
# Any cert in the full list not found in attached lists is unattached
```
```

## Step 8 — multi-account audit via Organizations (script)

**Audit certificates in each account:**

```bash
for ACCT_ID in $(aws organizations list-accounts \
  --query 'Accounts[?Status==`ACTIVE`].Id' --output text | tr '\t' '\n'); do
  CREDS=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$ACCT_ID:role/ACMMonitoringRole" \
    --role-session-name "acm-audit" --query 'Credentials' --output json)
  export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.AccessKeyId')
  export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.SecretAccessKey')
  export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.SessionToken')
  for REGION in us-east-1 us-west-2 eu-west-1; do
    echo "  $ACCT_ID / $REGION:"
    aws acm list-certificates --region "$REGION" \
      --query 'CertificateSummaryList[*].{Domain:DomainName,Status:Status}' --output table
  done
  unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
done
```

## Step 12 — private certificate (ACM PCA) monitoring (CLI)

```bash
# List private CAs and check expiry
aws acm-pca list-certificate-authorities \
  --query 'CertificateAuthorities[*].{Arn:Arn,Status:Status,NotAfter:NotAfter}' \
  --output table --region us-east-1

# PCA CA certs don't have a built-in DaysToExpiry metric.
# Compute days remaining from NotAfter:
NOT_AFTER=$(aws acm-pca describe-certificate-authority \
  --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/abc123 \
  --query 'CertificateAuthority.NotAfter' --output text --region us-east-1)
DAYS_REMAINING=$(( ( $(date -d "$NOT_AFTER" +%s) - $(date +%s) ) / 86400 ))
echo "PCA CA cert days remaining: $DAYS_REMAINING"
```
