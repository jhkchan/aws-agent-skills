# CRL and Revocation — ACM Private CA Deployer

Deep reference on CRL (Certificate Revocation List) configuration,
the S3 bucket policy requirement, OCSP support, certificate revocation
procedures, the CA deletion waiting period, and CloudTrail auditing.
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## CRL configuration

### How CRL works in ACM PCA

When CRL is enabled, ACM PCA publishes a Certificate Revocation List
to an S3 bucket at regular intervals. The CRL contains the serial
numbers of all revoked certificates. Clients can download the CRL and
check whether a certificate has been revoked before trusting it.

```text
CRL Publication Flow:
  1. Revoked certificate → revoke-certificate API call
  2. ACM PCA updates internal revocation state
  3. Next CRL publication cycle (based on ExpirationInDays):
     → ACM PCA writes updated CRL to S3 bucket
     → CRL object: s3://<bucket>/<ca-uuid>.crl
  4. Clients download CRL from the distribution point
     → Check certificate serial against CRL
     → If serial in CRL → certificate is revoked
```

### CRL configuration parameters

| Parameter | Description | Default |
|---|---|---|
| `Enabled` | Whether CRL is enabled | `false` |
| `S3BucketName` | S3 bucket for CRL publication | Required if enabled |
| `ExpirationInDays` | CRL validity before regeneration | 7 |
| `CustomCname` | Custom CNAME for CRL distribution point | None |

### The S3 bucket policy (critical)

The S3 bucket MUST have a policy granting the `acm-pca.amazonaws.com`
service principal the following permissions:

| Permission | Purpose |
|---|---|
| `s3:PutObject` | Write the CRL file to the bucket |
| `s3:PutObjectAcl` | Set the ACL on the CRL object (public-read for client access) |
| `s3:GetBucketAcl` | Read the bucket ACL before writing |
| `s3:GetBucketLocation` | Determine the bucket region |

**Without this policy, CRL publication silently fails.** No error is
returned. The CA appears to work, but the CRL is never published.
Clients relying on CRL for revocation checking will not see revoked
certificates — they will treat revoked certificates as valid.

### Bucket policy template

```bash
aws s3api put-bucket-policy \
  --bucket acm-pca-crl-123456789012-us-east-1 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "acm-pca.amazonaws.com"
        },
        "Action": [
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:GetBucketAcl",
          "s3:GetBucketLocation"
        ],
        "Resource": [
          "arn:aws:s3:::acm-pca-crl-123456789012-us-east-1",
          "arn:aws:s3:::acm-pca-crl-123456789012-us-east-1/*"
        ]
      }
    ]
  }'
```

### Making the CRL publicly readable

For clients to download the CRL, the CRL object should be publicly
readable. The `s3:PutObjectAcl` permission in the bucket policy allows
ACM PCA to set the ACL. You can also configure a bucket policy for
public read access:

```bash
aws s3api put-bucket-policy \
  --bucket acm-pca-crl-123456789012-us-east-1 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": { "Service": "acm-pca.amazonaws.com" },
        "Action": ["s3:PutObject", "s3:PutObjectAcl", "s3:GetBucketAcl", "s3:GetBucketLocation"],
        "Resource": [
          "arn:aws:s3:::acm-pca-crl-123456789012-us-east-1",
          "arn:aws:s3:::acm-pca-crl-123456789012-us-east-1/*"
        ]
      },
      {
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::acm-pca-crl-123456789012-us-east-1/*"
      }
    ]
  }'
```

### Custom CNAME for CRL distribution

The `CustomCname` parameter lets you specify a custom domain for the
CRL distribution point. This is useful when you want to use a CDN
(CloudFront) or a vanity domain for CRL access.

```bash
aws acm-pca create-certificate-authority \
  --revocation-configuration \
    "CrlConfiguration={Enabled=true,S3BucketName=acm-pca-crl-xxx,ExpirationInDays=7,CustomCname=crl.example.com}" \
  ...
```

The CRL distribution point in issued certificates will reference
`http://crl.example.com/<ca-uuid>.crl`.

## OCSP support

### How OCSP works in ACM PCA

OCSP (Online Certificate Status Protocol) provides real-time
certificate status checking. When a client receives a certificate,
it can query the OCSP responder (operated by ACM PCA) to check whether
the certificate is valid, revoked, or unknown.

```text
OCSP Flow:
  1. Client receives certificate during TLS handshake
  2. Client extracts OCSP responder URL from certificate AIA extension
  3. Client sends OCSP request to the responder
  4. ACM PCA OCSP responder checks revocation status in real-time
  5. Responder returns: GOOD | REVOKED | UNKNOWN
```

### Enabling OCSP

```bash
# At CA creation
aws acm-pca create-certificate-authority \
  --revocation-configuration \
    "OcspConfiguration={Enabled=true}" \
  --certificate-authority-type SUBORDINATE \
  ...

# On an existing CA
aws acm-pca update-certificate-authority \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --revocation-configuration \
    "OcspConfiguration={Enabled=true},CrlConfiguration={Enabled=true,S3BucketName=acm-pca-crl-xxx,ExpirationInDays=7}" \
  --region us-east-1
```

### OCSP vs CRL

| Feature | OCSP | CRL |
|---|---|---|
| Freshness | Real-time | Cached (updated every ExpirationInDays) |
| Client support | Some clients | Most clients |
| Infrastructure | Managed by AWS | S3 bucket (your responsibility) |
| Latency | One network round-trip per cert | Download once, cache locally |

**Recommendation:** enable both OCSP and CRL. OCSP provides real-time
status for clients that support it. CRL provides a fallback for
clients that do not.

## Certificate revocation

### Revoking a certificate

```bash
aws acm-pca revoke-certificate \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --certificate-serial 1234567890ABCDEF \
  --revocation-reason "KEY_COMPROMISE" \
  --region us-east-1
```

### Finding the certificate serial

The certificate serial is a hexadecimal string embedded in the
certificate. You can extract it from an issued certificate:

```bash
# Get the certificate
aws acm-pca get-certificate \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --certificate-arn "$CERT_ARN" --region us-east-1 | \
  jq -r '.Certificate' > cert.pem

# Extract the serial number
openssl x509 -in cert.pem -serial -noout
# Output: serial=1234567890ABCDEF
```

### Revocation reasons

| Reason | Code | When to use |
|---|---|---|
| `UNSPECIFIED` | 0 | No specific reason given |
| `KEY_COMPROMISE` | 1 | Private key compromised |
| `CERTIFICATE_AUTHORITY_COMPROMISE` | 2 | CA itself compromised |
| `AFFILIATION_CHANGED` | 3 | Subject affiliation changed |
| `SUPERCEDED` | 4 | Certificate superseded by newer one |
| `CESSATION_OF_OPERATION` | 5 | Service no longer operating |
| `PRIVILEGE_WITHDRAWN` | 6 | Privilege withdrawn |
| `A_A_COMPROMISE` | 7 | Attribute Authority compromised |

### Post-revocation behavior

After revocation:
- The certificate serial appears in the next CRL publication (if CRL
  is enabled).
- OCSP queries return REVOKED status (if OCSP is enabled).
- The certificate itself is NOT modified — it still has the same
  content and signature. Clients must check CRL/OCSP to discover
  the revocation.
- Applications that do not check revocation will still accept the
  certificate. This is a client-side configuration, not a server-side
  enforcement.

## CA deletion

### The mandatory waiting period

```bash
aws acm-pca delete-certificate-authority \
  --certificate-authority-arn "$CA_ARN" \
  --permanent-deletion-time-in-days 30 \
  --region us-east-1
```

| Phase | CA status | Can issue? | Can restore? |
|---|---|---|---|
| Before deletion | ACTIVE | Yes | N/A |
| After delete call | DELETED | No | Yes (restore-certificate-authority) |
| After waiting period | (gone) | No | No (permanently deleted) |

### Why the waiting period exists

The waiting period protects against accidental deletion. Certificates
issued by the CA may still be in active use. While the CA is in the
waiting period:
- Existing certificates remain valid (they carry the CA's signature).
- The CA is disabled (cannot issue new certificates).
- The CA can be fully restored to ACTIVE status.

After the waiting period expires:
- The CA is permanently deleted (private key destroyed).
- Existing certificates remain valid but CANNOT be revoked.
- No CRL updates can be published (the CA no longer exists).

### Restoring a deleted CA

```bash
aws acm-pca restore-certificate-authority \
  --certificate-authority-arn "$CA_ARN" \
  --region us-east-1
```

The CA returns to its previous status (ACTIVE or DISABLED).

### Best practice for decommissioning

1. Before deleting: revoke all outstanding certificates that should no
   longer be valid.
2. Set the waiting period to 30 days (maximum safety margin).
3. Monitor during the waiting period — if any critical certificate was
   missed, restore the CA and revoke it.
4. After confirming all certificates are handled, let the deletion
   proceed.

## CloudTrail auditing

All ACM PCA API calls are logged to CloudTrail. Key events:

```bash
# Query PCA events in the last 7 days
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=acm-pca.amazonaws.com \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --region us-east-1 \
  --query 'Events[*].{Event:EventName,Time:EventTime,User:Username}' \
  --output table
```

### Key events to monitor

| Event | What to check |
|---|---|
| `CreateCertificateAuthority` | Who created a CA and what configuration |
| `IssueCertificate` | Who issued a cert, what template, validity |
| `RevokeCertificate` | Who revoked, which serial, what reason |
| `CreatePermission` | Who granted access and to whom |
| `DeletePermission` | Who revoked access |
| `DeleteCertificateAuthority` | Who initiated deletion, waiting period |
| `ImportCertificateAuthorityCertificate` | Who activated a CA |

### Compliance reporting

For compliance audits, export the CloudTrail log to S3 and use Athena
to query:

```sql
SELECT eventname, eventtime, username, requestparameters
FROM cloudtrail_logs
WHERE eventsource = 'acm-pca.amazonaws.com'
  AND eventtime >= date '2026-01-01'
ORDER BY eventtime DESC;
```

## Common CRL and revocation pitfalls

1. **Missing bucket policy.** The #1 CRL pitfall. Without the policy,
   CRL publication silently fails. Always verify the policy after
   creating a CA with CRL.

2. **CRL not publicly accessible.** Even with the correct bucket
   policy, the CRL objects may not be publicly readable. Add a
   bucket policy granting `s3:GetObject` to `*` for the CRL path.

3. **Revoking after CA deletion.** Once the CA deletion waiting period
   expires, the CA is gone. You cannot revoke certificates issued by
   a deleted CA. Revoke before deleting.

4. **Not recording certificate serials.** You need the serial to
   revoke. Without it, revocation is impossible. Always record
   issued certificate serials.

5. **Assuming clients check CRL/OCSP.** Some clients (browsers, SDKs)
   do not check revocation by default. Revocation is only effective
   if clients check. Configure clients to check CRL/OCSP.

6. **Setting ExpirationInDays too high.** A 30-day CRL expiration
   means revoked certs may take up to 30 days to appear in the CRL.
   Use 7 days or less for timely revocation.

## Terraform CRL example

```hcl
resource "aws_acmpca_certificate_authority" "sub" {
  certificate_authority_configuration {
    key_algorithm     = "RSA_2048"
    signing_algorithm = "SHA256withRSA"
    subject {
      common_name  = "Example Subordinate CA"
      organization = "Example Org"
      country      = "US"
    }
  }

  revocation_configuration {
    crl_configuration {
      enabled            = true
      s3_bucket_name     = aws_s3_bucket.crl.id
      expiration_in_days = 7
      custom_cname       = "crl.example.com"
    }

    ocsp_configuration {
      enabled = true
    }
  }

  type  = "SUBORDINATE"
  tags  = { Environment = "production" }
}

resource "aws_s3_bucket" "crl" {
  bucket = "acm-pca-crl-123456789012-us-east-1"
}

resource "aws_s3_bucket_policy" "crl" {
  bucket = aws_s3_bucket.crl.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "acm-pca.amazonaws.com" }
        Action    = ["s3:PutObject", "s3:PutObjectAcl", "s3:GetBucketAcl", "s3:GetBucketLocation"]
        Resource  = [aws_s3_bucket.crl.arn, "${aws_s3_bucket.crl.arn}/*"]
      },
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.crl.arn}/*"
      }
    ]
  })
}
```
