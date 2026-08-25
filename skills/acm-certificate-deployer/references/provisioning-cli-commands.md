# Provisioning CLI Commands — ACM Certificate Deployer

Full copy-pasteable CLI command sequence for provisioning AWS
Certificate Manager certificates with DNS validation, CloudFront
integration, private certificates, and third-party import. Variables
to substitute: `<domain>`, `<region>`, `<account-id>`, `<zone-id>`,
`<cert-arn>`, `<distribution-id>`.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region (MUST be us-east-1 for CloudFront)
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm Route53 hosted zone for the domain
aws route53 list-hosted-zones-by-name --dns-name <domain> \
  --query 'HostedZones[0].Id' --output text
```

## Step 1: Request a public certificate with DNS validation

```bash
CERT_ARN=$(aws acm request-certificate \
  --domain-name example.com \
  --subject-alternative-names "*.example.com" \
  --validation-method DNS \
  --key-algorithm RSA_2048 \
  --region us-east-1 \
  --tags Key=Environment,Value=production \
  --query CertificateArn --output text)

echo "Certificate ARN: $CERT_ARN"
```

## Step 2: Retrieve the DNS validation CNAME records

```bash
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[*].ResourceRecord' \
  --output table
```

Output format:
```
----------------------------------------------------------------------
|                          DescribeCertificate                        |
+---------------------------------------------------+-----------------+
|                     Name                          |     Value       |
+---------------------------------------------------+-----------------+
| _a79865b4a8b5d1ce2345678901234567.example.com.    |  _c3a1...aws.   |
| _b89865b4a8b5d1ce2345678901234567.example.com.    |  _d4b2...aws.   |
+---------------------------------------------------+-----------------+
```

## Step 3: Add the CNAME records to Route53

```bash
# For each CNAME record from Step 2:
aws route53 change-resource-record-sets \
  --hosted-zone-id Z2KVMGOMGDOOU2 \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "_<random>.example.com.",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "_<random>.acm-validations.aws."}]
      }
    }]
  }'
```

## Step 4: Wait for certificate issuance

```bash
aws acm wait certificate-validated \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1

# Verify status
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1 \
  --query 'Certificate.Status' --output text
# Expected: ISSUED
```

## Step 5: Attach to CloudFront (us-east-1 required)

```bash
# Get current distribution config + ETag
CONFIG=$(aws cloudfront get-distribution-config \
  --id E1234567890ABC \
  --query 'DistributionConfig')

ETAG=$(aws cloudfront get-distribution-config \
  --id E1234567890ABC \
  --query 'ETag' --output text)

# Update the ViewerCertificate in the config (use jq)
echo "$CONFIG" | jq --arg arn "$CERT_ARN" '
  .ViewerCertificate = {
    "CloudFrontDefaultCertificate": false,
    "AcmCertificateArn": $arn,
    "SslSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021"
  }
' > /tmp/updated-config.json

aws cloudfront update-distribution \
  --id E1234567890ABC \
  --if-match "$ETAG" \
  --distribution-config file:///tmp/updated-config.json
```

## Step 6: Import a third-party certificate (PEM)

```bash
aws acm import-certificate \
  --certificate fileb://certificate.pem \
  --private-key fileb://private-key.pem \
  --certificate-chain fileb://chain.pem \
  --region us-east-1 \
  --tags Key=Environment,Value=production Key=Source,Value=external-ca
```

## Step 7: Request a private certificate (via AWS Private CA)

```bash
# Prerequisite: Private CA must exist and be ACTIVE
PCA_ARN="arn:aws:acm-pca:us-east-1:<account-id>:certificate-authority/<uuid>"

aws acm request-certificate \
  --domain-name internal.example.com \
  --subject-alternative-names "*.internal.example.com" \
  --validation-method DNS \
  --certificate-authority-arn "$PCA_ARN" \
  --region us-east-1
```

## Step 8: Export a private certificate (for use outside AWS)

```bash
aws acm export-certificate \
  --certificate-arn <private-cert-arn> \
  --passphrase fileb://passphrase.txt \
  --region us-east-1 \
  --query 'Certificate' --output text > exported-cert.pem
```

## Step 9: Share a Private CA cross-account

```bash
# In the PCA-owning account
aws acm-pca create-permission \
  --certificate-authority-arn "$PCA_ARN" \
  --principal <consumer-account-id> \
  --actions IssueCertificate GetCertificate ListPermissions
```

## Verification

```bash
# List all certificates in the region
aws acm list-certificates --region us-east-1

# Get certificate details (status, domain names, validation, renewal)
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1

# Verify the DNS validation CNAME exists in Route53
aws route53 list-resource-record-sets \
  --hosted-zone-id Z2KVMGOMGDOOU2 \
  --query "ResourceRecordSets[?Type=='CNAME']"

# Verify CloudFront attachment
aws cloudfront get-distribution-config \
  --id E1234567890ABC \
  --query 'DistributionConfig.ViewerCertificate.AcmCertificateArn'

# Check Private CA status
aws acm-pca describe-certificate-authority \
  --certificate-authority-arn "$PCA_ARN"
```

## Terraform equivalent

```hcl
# Public certificate with DNS validation
resource "aws_acm_certificate" "cert" {
  domain_name               = "example.com"
  subject_alternative_names = ["*.example.com"]
  validation_method         = "DNS"
  key_algorithm             = "RSA_2048"
  lifecycle {
    create_before_destroy = true
  }
}

# Route53 validation record (auto-created)
resource "aws_route53_record" "validation" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.main.zone_id
}

# Validation complete
resource "aws_acm_certificate_validation" "cert" {
  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = [for record in aws_route53_record.validation : record.fqdn]
}

# CloudFront distribution using the certificate (must be us-east-1)
resource "aws_cloudfront_distribution" "cdn" {
  # ... viewer_certificate block ...
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.cert.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| Request certificate | `aws acm request-certificate` |
| Describe certificate | `aws acm describe-certificate` |
| List certificates | `aws acm list-certificates` |
| Resend validation email | `aws acm resend-validation-email` |
| Import certificate | `aws acm import-certificate` |
| Export private certificate | `aws acm export-certificate` |
| Delete certificate | `aws acm delete-certificate` |
| Add tags | `aws acm add-tags-to-certificate` |
| List PCA CAs | `aws acm-pca list-certificate-authorities` |
| Create PCA permission | `aws acm-pca create-permission` |
| Wait for validation | `aws acm wait certificate-validated` |

## Step 3 — request with DNS validation (CLI)

```bash
aws acm request-certificate \
  --domain-name example.com \
  --subject-alternative-names "*.example.com" \
  --validation-method DNS \
  --region us-east-1
```

## Step 3 — retrieve the CNAME records (CLI)

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:<acct>:certificate/<uuid> \
  --query 'Certificate.DomainValidationOptions[*].ResourceRecord' \
  --region us-east-1
```

## Step 3 — add the CNAME to Route53 (CLI)

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z2KVMGOMGDOOU2 \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "_<random>.example.com.",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "_<random>.acm-validations.aws."}]
      }
    }]
  }'
```

## Step 7 — attach certificate to CloudFront (CLI)

```bash
aws cloudfront update-distribution \
  --id E1234567890ABC \
  --distribution-config '{
    "ViewerCertificate": {
      "AcmCertificateArn": "arn:aws:acm:us-east-1:<acct>:certificate/<uuid>",
      "SslSupportMethod": "sni-only",
      "MinimumProtocolVersion": "TLSv1.2_2021"
    },
    ... (rest of distribution config)
  }'
```

## Step 8 — share a Private CA cross-account (CLI)

```bash
# In the PCA-owning account
aws acm-pca create-permission \
  --certificate-authority-arn arn:aws:acm-pca:us-east-1:<acct>:certificate-authority/<uuid> \
  --principal <consumer-account-id> \
  --actions IssueCertificate GetCertificate ListPermissions
```

## Step 9 — private certificate workflow (CLI)

```bash
# Step 1: Create a Private CA (one-time)
aws acm-pca create-certificate-authority \
  --certificate-authority-configuration '{
    "KeyAlgorithm": "RSA_2048",
    "SigningAlgorithm": "SHA256WITHRSA",
    "Subject": {"CommonName": "My Private CA"}
  }' \
  --certificate-authority-type "SUBORDINATE" \
  --region us-east-1

# Step 2: Install the CA certificate (sign the CSR)
aws acm-pca issue-certificate \
  --certificate-authority-arn <ca-arn> \
  --csr fileb://ca-csr.pem \
  --signing-algorithm SHA256WITHRSA \
  --validity Value=10,Type=YEARS

# Step 3: Request a private certificate via ACM
aws acm request-certificate \
  --domain-name internal.example.com \
  --certificate-authority-arn <ca-arn> \
  --validation-method DNS \
  --region us-east-1
```
