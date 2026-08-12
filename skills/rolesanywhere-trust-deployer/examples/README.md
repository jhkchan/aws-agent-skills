# End-to-End Example: Roles Anywhere Trust Deployment

A walkthrough showing how to use the `rolesanywhere-trust-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an IAM Roles Anywhere trust infrastructure that
allows an external CI runner to assume an IAM role using an X.509
certificate from your self-managed PKI instead of long-lived AWS
access keys. The infrastructure needs:

- External CA: self-managed (ca-cert.pem)
- Trust anchor: prod-pki-trust-anchor (CERTIFICATE_BUNDLE source)
- Profile: ci-runner-profile (maps cert to role, session duration 3600s)
- Session policy: restrict to s3:GetObject on my-ci-artifacts/*
- IAM role: RolesAnywhereCIRunner (trust rolesanywhere.amazonaws.com)
- IAM permissions: AmazonS3ReadOnlyAccess
- Revocation: CRL configured (prod-pki-crl)
- Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-rolesanywhere-trust
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Roles Anywhere trust anchor binding my external
      CA. Map it to an IAM role via a profile. Configure the
      credential helper and CRL revocation."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a roles anywhere trust anchor"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ROLES_ANYWHERE: ta-aaa111222 → p-bbb222333 → arn:aws:iam::123456789012:role/RolesAnywhereCIRunner
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Trust anchor: ta-aaa111222 — self-managed CA (CERTIFICATE_BUNDLE, ca-cert.pem)
  [✓] Profile: p-bbb222333 — roleArns: arn:aws:iam::123456789012:role/RolesAnywhereCIRunner (duration: 3600s)
  [✓] IAM role: arn:aws:iam::123456789012:role/RolesAnywhereCIRunner (trust: rolesanywhere.amazonaws.com; permissions: AmazonS3ReadOnlyAccess)
  [✓] Session policy: inline — restrict to s3:GetObject on my-ci-artifacts/*
  [✓] Credential helper: aws_signing_helper (client-side, cert: client-cert.pem)
  [✓] Revocation: CRL configured (prod-pki-crl)
  [✓] CloudTrail audit: AssumeRoot events logged
  [✓] CA certificate verified: ca-cert.pem (PEM, expires 2027-12-31)
  [✓] Client certificate verified: client-cert.pem (PEM, expires 2026-11-01)
  [✓] Region: us-east-1
  [✓] Tags: Environment=production, Workload=ci-runner
VERIFICATION_COMMANDS:
  aws rolesanywhere list-trust-anchors --region us-east-1
  aws rolesanywhere list-profiles --region us-east-1
  aws iam get-role --role-name RolesAnywhereCIRunner
  ./aws_signing_helper credential-process --certificate client-cert.pem --private-key client-key.pem --trust-anchor-id ta-aaa111222 --profile-id p-bbb222333 --role-arn arn:aws:iam::123456789012:role/RolesAnywhereCIRunner --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the trust anchor (bind CA to AWS IAM)
CA_CERT=$(cat ca-cert.pem)
TRUST_ANCHOR_ID=$(aws rolesanywhere create-trust-anchor \
  --name "prod-pki-trust-anchor" \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$CA_CERT}" \
  --enabled --region us-east-1 \
  --query 'trustAnchor.trustAnchorId' --output text)

# Step 2: Create the IAM role with Roles Anywhere trust policy
aws iam create-role --role-name RolesAnywhereCIRunner \
  --assume-role-policy-document file://trust-policy.json --region us-east-1

aws iam attach-role-policy --role-name RolesAnywhereCIRunner \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Step 3: Create the profile (map cert to role with session policy)
PROFILE_ID=$(aws rolesanywhere create-profile \
  --name "ci-runner-profile" \
  --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --role-arns "arn:aws:iam::123456789012:role/RolesAnywhereCIRunner" \
  --session-policy file://session-policy.json \
  --duration-seconds 3600 --enabled --region us-east-1 \
  --query 'profile.profileId' --output text)

# Step 4: Configure revocation (CRL)
aws rolesanywhere enable-crl \
  --crl-name "prod-pki-crl" \
  --crl-data "$(base64 crl.pem)" \
  --trust-anchor-arn "arn:aws:rolesanywhere:us-east-1:123456789012:trust-anchor/$TRUST_ANCHOR_ID" \
  --region us-east-1

# Step 5: Download and configure the credential helper (on the client)
curl -o aws_signing_helper \
  https://rolesanywhere-helper-tool.s3.us-west-2.amazonaws.com/latest/aws_signing_helper_darwin_arm64
chmod +x aws_signing_helper
```

---

## Step 4 — Post-deployment verification

```bash
# Trust anchor — verify it exists and is enabled
aws rolesanywhere list-trust-anchors --region us-east-1 \
  --query 'trustAnchors[*].{ID:trustAnchorId,Name:name,Enabled:enabled}' \
  --output table

# Profile — verify role mapping and session policy
aws rolesanywhere list-profiles --region us-east-1 \
  --query 'profiles[*].{ID:profileId,Name:name,Roles:roleArns}' \
  --output table

# IAM role — verify trust policy includes rolesanywhere.amazonaws.com
aws iam get-role --role-name RolesAnywhereCIRunner \
  --query 'Role.AssumeRolePolicyDocument.Statement[*].Principal.Service' \
  --output text

# Credential helper — exchange cert for STS credentials
./aws_signing_helper credential-process \
  --certificate client-cert.pem \
  --private-key client-key.pem \
  --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --profile-id "$PROFILE_ID" \
  --role-arn arn:aws:iam::123456789012:role/RolesAnywhereCIRunner \
  --region us-east-1

# Verify the temporary credentials work
AWS_PROFILE=rolesanywhere aws sts get-caller-identity

# CloudTrail audit — verify AssumeRoot events are logged
aws cloudtrail lookup-events \
  --lookup-attributes "AttributeKey=EventName,AttributeValue=AssumeRoot" \
  --start-time "$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --region us-east-1 --output table
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| IAM trust policy | Often forgotten | rolesanywhere.amazonaws.com principal | Without it, assume fails with AccessDenied |
| Session policy | Not configured | Inline session policy restricting permissions | Session policies RESTRICT; scope down shared roles |
| Revocation (CRL) | Not configured | CRL attached to trust anchor | Without it, compromised certs remain valid until expiry |
| Credential helper | Partial command | Full credential-process with all flags | Missing flags cause opaque errors |
| Three-legged stool | Only trust anchor | Trust anchor + profile + IAM role | All three required; missing any = AccessDenied |
| CA verification | Not checked | openssl x509 verification | Invalid CA cert = trust anchor creation fails |

---

## Related artifacts

- **Skill definition:** `skills/rolesanywhere-trust-deployer/SKILL.md`
- **Trust anchor and profile guide:** `skills/rolesanywhere-trust-deployer/references/trust-anchor-and-profile.md`
- **Credential helper and revocation guide:** `skills/rolesanywhere-trust-deployer/references/credential-helper-and-revocation.md`
- **Slash command:** `commands/aws/deploy-rolesanywhere-trust.md`
- **Eval suite:** `skills/rolesanywhere-trust-deployer/evals/evals.json`
- **Legacy test cases:** `skills/rolesanywhere-trust-deployer/eval/test-cases.yaml`
