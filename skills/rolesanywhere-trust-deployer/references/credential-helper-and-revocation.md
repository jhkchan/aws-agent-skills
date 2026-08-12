# Credential Helper and Revocation — Roles Anywhere Trust Deployer

Deep reference on the AWS signing helper (credential-process mode,
certificate/private-key signing, AWS CLI credential_process integration,
debugging common errors), certificate revocation (CRL creation and
update, OCSP comparison, revocation enforcement behavior), and
CloudTrail audit (AssumeRoot events, key fields, querying sessions).
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## AWS signing helper

### What the signing helper does

The AWS signing helper (`aws_signing_helper`) is a client-side binary
that exchanges an X.509 certificate for STS temporary credentials. It
signs the AssumeRole request with the certificate's private key,
proving possession. Without it, the workload cannot authenticate to
AWS via Roles Anywhere.

### Downloading the signing helper

Download the binary for your platform from the AWS Roles Anywhere
helper tool S3 bucket:

| Platform | URL |
|---|---|
| macOS arm64 | `https://rolesanywhere-helper-tool.s3.us-west-2.amazonaws.com/latest/aws_signing_helper_darwin_arm64` |
| macOS x86_64 | `https://rolesanywhere-helper-tool.s3.us-west-2.amazonaws.com/latest/aws_signing_helper_darwin_amd64` |
| Linux x86_64 | `https://rolesanywhere-helper-tool.s3.us-west-2.amazonaws.com/latest/aws_signing_helper_linux_amd64` |
| Windows | `https://rolesanywhere-helper-tool.s3.us-west-2.amazonaws.com/latest/aws_signing_helper_windows_amd64.exe` |

```bash
curl -o aws_signing_helper \
  https://rolesanywhere-helper-tool.s3.us-west-2.amazonaws.com/latest/aws_signing_helper_darwin_arm64
chmod +x aws_signing_helper
```

### credential-process mode (recommended)

The `credential-process` subcommand outputs JSON compatible with the
AWS CLI credential process feature:

```bash
./aws_signing_helper credential-process \
  --certificate client-cert.pem \
  --private-key client-key.pem \
  --trust-anchor-id ta-aaa111222 \
  --profile-id p-bbb222333 \
  --role-arn arn:aws:iam::123456789012:role/RolesAnywhereCIRunner \
  --region us-east-1
```

Output:

```json
{
  "Version": 1,
  "AccessKeyId": "ASIA...",
  "SecretAccessKey": "...",
  "SessionToken": "...",
  "Expiration": "2026-08-11T12:00:00Z"
}
```

### AWS CLI credential_process integration

Configure the AWS CLI to use the signing helper as a credential
process. The CLI automatically refreshes credentials before they
expire.

```ini
[profile rolesanywhere]
credential_process = /path/to/aws_signing_helper credential-process --certificate /path/to/client-cert.pem --private-key /path/to/client-key.pem --trust-anchor-id ta-aaa111222 --profile-id p-bbb222333 --role-arn arn:aws:iam::123456789012:role/RolesAnywhereCIRunner --region us-east-1
region = us-east-1
```

Then use the profile normally:

```bash
AWS_PROFILE=rolesanywhere aws s3 ls
AWS_PROFILE=rolesanywhere aws sts get-caller-identity
```

### serve-proxy mode (for SDKs that do not support credential_process)

For SDKs that do not support credential_process, the signing helper
can run as a local HTTP proxy that injects credentials into requests:

```bash
./aws_signing_helper serve-proxy \
  --certificate client-cert.pem \
  --private-key client-key.pem \
  --trust-anchor-id ta-aaa111222 \
  --profile-id p-bbb222333 \
  --role-arn arn:aws:iam::123456789012:role/RolesAnywhereCIRunner \
  --region us-east-1
```

Then configure the SDK to use `http://localhost:localhost-port` as
the HTTP proxy.

### Common signing helper errors

| Error | Cause | Fix |
|---|---|---|
| `AccessDenied` | IAM role trust policy missing rolesanywhere.amazonaws.com principal | Add the principal to the role trust policy |
| `Certificate not signed by trusted CA` | Certificate chain does not match the trust anchor's CA | Verify: `openssl verify -CAfile ca-cert.pem client-cert.pem` |
| `Certificate expired` | Certificate past expiration | Generate a new certificate from the CA |
| `Profile not found` | Profile ID does not exist or is disabled | Verify: `aws rolesanywhere list-profiles` |
| `Role not in profile` | Role ARN not in the profile's roleArns list | Add the role ARN to the profile |
| `Private key does not match certificate` | Private key is not the pair for the certificate | Regenerate the key pair and certificate |

## Certificate revocation

### Why revocation matters

By default, a certificate remains valid until its expiration date. To
revoke a certificate before expiration (e.g., if it is compromised),
you must configure a Certificate Revocation List (CRL). Without a CRL,
a compromised certificate remains usable until it expires. This is the
#1 cause of "we revoked the cert in the CA but AWS still accepts it"
incidents.

### CRL vs OCSP

| Mechanism | Description | Roles Anywhere support |
|---|---|---|
| CRL (Certificate Revocation List) | A signed list of revoked certificate serial numbers, published by the CA. | Supported |
| OCSP (Online Certificate Status Protocol) | Real-time revocation checking via an OCSP responder. | Not directly supported by Roles Anywhere |

Roles Anywhere uses CRL-based revocation. If your PKI uses OCSP, you
must generate a CRL from your CA for use with Roles Anywhere.

### Creating a CRL

Generate a CRL in your CA:

```bash
openssl ca -gencrl -out crl.pem
```

Create the CRL in Roles Anywhere:

```bash
CRL_ID=$(aws rolesanywhere enable-crl \
  --crl-name "prod-pki-crl" \
  --crl-data "$(base64 crl.pem)" \
  --trust-anchor-arn "arn:aws:rolesanywhere:us-east-1:123456789012:trust-anchor/ta-aaa111222" \
  --region us-east-1 \
  --query 'crl.crlId' --output text)
```

### Updating the CRL

When you revoke a certificate in your CA, regenerate the CRL and
update it in Roles Anywhere:

```bash
# Revoke the certificate in your CA
openssl ca -revoke client-cert.pem

# Regenerate the CRL
openssl ca -gencrl -out crl.pem

# Update the CRL in Roles Anywhere
aws rolesanywhere update-crl \
  --crl-id "$CRL_ID" \
  --crl-data "$(base64 crl.pem)" \
  --region us-east-1
```

### CRL enforcement behavior

- Roles Anywhere checks the CRL at credential issuance time (when the
  signing helper requests temporary credentials).
- If a certificate's serial number is on the CRL, the request is
  rejected.
- Existing sessions (already-issued credentials) are NOT immediately
  revoked. They remain valid until they expire. To revoke active
  sessions, reduce the session duration or revoke the IAM role's
  active sessions via STS.

### CRL distribution point

For automatic CRL updates, configure a CRL distribution point (an
HTTP(S) endpoint where the CRL is published). Roles Anywhere can
fetch the CRL from the distribution point on a schedule.

```bash
aws rolesanywhere enable-crl \
  --crl-name "prod-pki-crl" \
  --crl-data "$(base64 crl.pem)" \
  --trust-anchor-arn "arn:aws:rolesanywhere:us-east-1:123456789012:trust-anchor/ta-aaa111222" \
  --region us-east-1
```

## CloudTrail audit (AssumeRoot)

### AssumeRoot events

Roles Anywhere sessions are logged in CloudTrail under the `AssumeRoot`
event name. The source is `rolesanywhere.amazonaws.com`.

### Querying AssumeRoot events

```bash
aws cloudtrail lookup-events \
  --lookup-attributes "AttributeKey=EventName,AttributeValue=AssumeRoot" \
  --start-time "$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --region us-east-1 \
  --query 'Events[*].{Time:EventTime,User:Username,Role:EventName}' \
  --output table
```

### Key fields in AssumeRoot events

| Field | Description |
|---|---|
| `eventName` | `AssumeRoot` |
| `eventSource` | `rolesanywhere.amazonaws.com` |
| `requestParameters.profileArn` | The profile used |
| `requestParameters.trustAnchorArn` | The trust anchor used |
| `requestParameters.roleArn` | The IAM role assumed |
| `userIdentity.sessionContext.sessionIssuer.arn` | The IAM role ARN |
| `sourceIPAddress` | The client IP address |
| `readOnly` | Whether the event is a read-only operation |

### Auditing which certificates assumed which roles

```bash
aws cloudtrail lookup-events \
  --lookup-attributes "AttributeKey=EventName,AttributeValue=AssumeRoot" \
  --start-time "2026-08-01T00:00:00Z" \
  --end-time "2026-08-11T23:59:59Z" \
  --region us-east-1 \
  --output json | jq '.Events[].CloudTrailEvent | fromjson | {
    time: eventTime,
    role: .requestParameters.roleArn,
    profile: .requestParameters.profileArn,
    trustAnchor: .requestParameters.trustAnchorArn,
    sourceIP: sourceIPAddress
  }'
```

This produces a chronological list of all Roles Anywhere sessions,
including which profile and trust anchor were used and which role was
assumed.

## Terraform examples

### CRL resource

```hcl
resource "aws_rolesanywhere_crl" "revocation" {
  name             = "prod-pki-crl"
  crl_data         = base64encode(file("crl.pem"))
  trust_anchor_arn = aws_rolesanywhere_trust_anchor.external.arn
}
```

### Updating the CRL via a Lambda function (automated)

```python
import boto3
import subprocess
import base64

rolesanywhere = boto3.client('rolesanywhere')

def lambda_handler(event, context):
    # Regenerate the CRL from the CA
    subprocess.run(['openssl', 'ca', '-gencrl', '-out', '/tmp/crl.pem'])
    
    # Read and base64-encode the CRL
    with open('/tmp/crl.pem', 'rb') as f:
        crl_data = base64.b64encode(f.read()).decode()
    
    # Update the CRL in Roles Anywhere
    response = rolesanywhere.update_crl(
        crlId='crl-xxx',
        crlData=crl_data
    )
    
    return {'statusCode': 200, 'body': 'CRL updated'}
```

Trigger this Lambda on a schedule (e.g., every hour) via EventBridge
to keep the CRL up to date automatically.
