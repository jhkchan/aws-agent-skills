# End-to-End Example: ACM Certificate Deployment

A walkthrough showing how to use the `acm-certificate-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a public wildcard TLS certificate for a
CloudFront distribution. The certificate needs:

- Certificate type: Public (browser-trusted)
- Domain names: example.com + *.example.com (apex + wildcard)
- Validation method: DNS (Route53 CNAME)
- Region: us-east-1 (required for CloudFront)
- CloudFront distribution: E1234567890ABC
- Key algorithm: RSA_2048
- Tags: Environment=production, Service=website

Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-acm-certificate
```

Then paste the requirements.

### Option B: Natural language

```
You: "Request a public ACM certificate for example.com and
      *.example.com with DNS validation in us-east-1. Attach it to
      CloudFront distribution E1234567890ABC. Route53 zone
      Z2KVMGOMGDOOU2. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "request an acm certificate"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ACM_CERTIFICATE: *.example.com (arn:aws:acm:us-east-1:123456789012:certificate/abc-123)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Certificate type: Public
  [✓] Domain names: example.com, *.example.com
  [✓] Validation method: DNS (recommended)
  [✓] DNS validation CNAME: added to Route53 zone Z2KVMGOMGDOOU2
  [✓] Certificate status: ISSUED
  [✓] Key algorithm: RSA_2048
  [✓] Renewal: Automatic (ACM-managed, 60 days before expiry)
  [✓] Region: us-east-1 (required for CloudFront)
  [✓] CloudFront integration: E1234567890ABC → cert in us-east-1
  [✓] Cross-account sharing: Same account (no sharing needed)
  [✓] Tags: Environment=production, Service=website
VERIFICATION_COMMANDS:
  aws acm describe-certificate --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc-123
  aws acm list-certificates --region us-east-1
  aws route53 list-resource-record-sets --hosted-zone-id Z2KVMGOMGDOOU2
  aws cloudfront get-distribution-config --id E1234567890ABC
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Request the certificate
CERT_ARN=$(aws acm request-certificate \
  --domain-name example.com \
  --subject-alternative-names "*.example.com" \
  --validation-method DNS \
  --key-algorithm RSA_2048 \
  --region us-east-1 \
  --tags Key=Environment,Value=production Key=Service,Value=website \
  --query CertificateArn --output text)

# Step 2: Retrieve CNAME records
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[*].ResourceRecord'

# Step 3: Add CNAMEs to Route53 (for each record)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z2KVMGOMGDOOU2 \
  --change-batch '{...}'

# Step 4: Wait for issuance
aws acm wait certificate-validated \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1

# Step 5: Attach to CloudFront
aws cloudfront update-distribution \
  --id E1234567890ABC \
  --distribution-config '{...ViewerCertificate...}'
```

---

## Step 4 — Post-deployment verification

```bash
# Certificate status — Status: ISSUED, RenewalEligibility: ELIGIBLE
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1

# CloudFront — ViewerCertificate.AcmCertificateArn matches
aws cloudfront get-distribution-config \
  --id E1234567890ABC \
  --query 'DistributionConfig.ViewerCertificate'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Region | Any region | us-east-1 (for CloudFront) | CloudFront requires us-east-1; other regions are invisible |
| Domain names | Wildcard only | Apex + wildcard | `*.example.com` does NOT cover `example.com` |
| Validation method | Email or unspecified | DNS validation | Email is deprecated; DNS is automatable + auto-renews |
| CNAME persistence | Removes CNAME after issuance | CNAME must remain | ACM re-validates; removing CNAME blocks renewal |
| Imported cert renewal | Assumes auto-renew | Manual re-import | ACM does NOT auto-renew imported certificates |
| Private cert scope | Uses private cert publicly | Public cert for public endpoints | Private certs are NOT browser-trusted |

---

## Related artifacts

- **Skill definition:** `skills/acm-certificate-deployer/SKILL.md`
- **Validation and renewal guide:** `skills/acm-certificate-deployer/references/validation-and-renewal.md`
- **Provisioning CLI commands:** `skills/acm-certificate-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-acm-certificate.md`
- **Eval suite:** `skills/acm-certificate-deployer/evals/evals.json`
- **Legacy test cases:** `skills/acm-certificate-deployer/eval/test-cases.yaml`
