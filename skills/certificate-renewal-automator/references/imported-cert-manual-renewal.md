# Imported Certificate Manual Renewal Reference

Supplementary reference for the Certificate Renewal Automator skill.
Use when an imported (private-key) certificate requires renewal —
ACM cannot auto-renew these, so a full manual or semi-automated flow
is required.

## Why imported certs need manual renewal

ACM stores private keys only for certificates it issues. When a cert is
imported via `acm import-certificate`, ACM stores the cert and key for
serving but has NO access to the issuing CA's renewal infrastructure.
The `RenewalEligibility` is always `INELIGIBLE` for imported certs.

## Full manual renewal flow

### Step 1: Identify the external CA

```bash
# Check the cert issuer
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:111111111111:certificate/def-456 \
  --query 'Certificate.[DomainName,Status,NotBefore,NotAfter,Serial]'
```

The serial and dates identify the cert at the external CA (DigiCert,
Let's Encrypt, internal PKI, etc.).

### Step 2: Renew at the external CA

This step happens entirely outside AWS. The operator (or automation)
renews the cert at the external CA's portal/API and receives:
- New certificate PEM
- New private key PEM (or reuses the existing key if the CA allows)
- Certificate chain PEM (intermediate + root)

### Step 3: Re-import the renewed certificate

```bash
# Option A: Re-import to the SAME ARN (cert must not be expired yet)
aws acm import-certificate \
  --certificate-arn arn:aws:acm:us-east-1:111111111111:certificate/def-456 \
  --certificate fileb://new-cert.pem \
  --private-key fileb://new-key.pem \
  --certificate-chain fileb://new-chain.pem

# Option B: Import as a NEW certificate (creates new ARN)
aws acm import-certificate \
  --certificate fileb://new-cert.pem \
  --private-key fileb://new-key.pem \
  --certificate-chain fileb://new-chain.pem \
  --tags Key=ManagedBy,Value=cert-renewal-automator
```

**Option A** is preferred — the ARN stays the same, so no listener or
distribution updates are needed. BUT: the cert must NOT have expired
yet. If the cert has already expired, Option A fails and Option B is
required (then update all references).

### Step 4: Update resource references (Option B only)

If a new ARN was created:

```bash
# ALB listener
aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:us-east-1:111111111111:listener/app/my-alb/abc/def \
  --certificates CertificateArn=arn:aws:acm:us-east-1:111111111111:certificate/new-arn

# CloudFront
aws cloudfront update-distribution --id E123456 --if-match <etag> \
  --distribution-config file://updated-config.json

# API Gateway REST
aws apigateway update-domain-name --domain-name api.example.com \
  --patch-operations op=replace,path=/certificateArn,value=arn:aws:acm:us-east-1:111111111111:certificate/new-arn
```

### Step 5: Verify via SNI

```bash
openssl s_client -connect <endpoint>:443 -servername <domain> \
  </dev/null 2>/dev/null | openssl x509 -noout -subject -dates -issuer
```

### Step 6: Delete the old certificate (Option B only)

```bash
# Verify old cert is not in use
aws acm describe-certificate \
  --certificate-arn <old-arn> \
  --query 'Certificate.InUseBy'

# If InUseBy is empty, safe to delete
aws acm delete-certificate --certificate-arn <old-arn>
```

## Semi-automated renewal via Lambda

For organizations with many imported certs, a semi-automated Lambda can
handle steps 3-6 when triggered by an SNS notification from the daily
cert-scan Lambda. The Lambda would:

1. Receive the cert ARN and days-to-expiry from the scan.
2. Fetch the renewed cert from a pre-configured S3 bucket (where the
   external CA renewal automation drops the renewed PEM files).
3. Call `import-certificate` (Option A — re-import to same ARN).
4. Verify via SNI.
5. Publish success/failure to SNS.

```python
import boto3
acm = boto3.client('acm')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    cert_arn = event['certificate_arn']
    cert_id = cert_arn.split('/')[-1]

    # Fetch renewed cert files from S3 (dropped by external CA automation)
    cert = s3.get_object(Bucket='cert-renewal-bucket', Key=f'{cert_id}/cert.pem')['Body'].read()
    key = s3.get_object(Bucket='cert-renewal-bucket', Key=f'{cert_id}/key.pem')['Body'].read()
    chain = s3.get_object(Bucket='cert-renewal-bucket', Key=f'{cert_id}/chain.pem')['Body'].read()

    # Re-import to same ARN
    acm.import_certificate(
        CertificateArn=cert_arn,
        Certificate=cert, PrivateKey=key, CertificateChain=chain
    )
    return {'status': 'renewed', 'arn': cert_arn}
```

## Migration path: imported cert to DNS-validated ACM cert

To eliminate the manual renewal burden permanently, migrate imported
certs to DNS-validated ACM certs:

1. Request a new DNS-validated cert for the same domain.
2. Add the DNS validation CNAME to Route 53.
3. Wait for issuance.
4. Update all resource references to the new ARN.
5. Delete the old imported cert.

This converts the renewal path from manual (Path 4) to managed (Path 1)
and eliminates all future manual renewal work.

## Audit trail

All import-certificate calls are logged to CloudTrail:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ImportCertificate \
  --start-time $(date -v-7d +%Y-%m-%dT%H:%M:%S)
```

This provides a forensic record of all certificate imports, including
the caller identity and source IP — useful for compliance audits.
