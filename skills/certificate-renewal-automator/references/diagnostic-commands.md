# certificate-renewal-automator — diagnostic commands (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## Cert-scan Lambda (EventBridge daily scan target, Step 3)

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

## CloudTrail audit commands (Step 12)

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
