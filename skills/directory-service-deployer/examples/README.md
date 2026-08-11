# End-to-End Example: Directory Service Deployment

A walkthrough showing how to use the `directory-service-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Managed Microsoft AD Enterprise directory
with a two-way forest trust to an on-prem domain, LDAPS enabled,
and IAM Identity Center SSO. The deployment needs:

- Directory type: Managed Microsoft AD
- Edition: Enterprise
- VPC: vpc-aaa11122 (enableDnsSupport=true, enableDnsHostnames=true)
- Subnets: subnet-aaa111 (us-east-1a), subnet-bbb222 (us-east-1b)
- DNS name: corp.example.com
- Trust: Two-Way Forest trust with onprem.example.com
- LDAPS: enabled (cert from AWS PCA, expires 2026-12-01)
- SSO: IAM Identity Center connected
- Password policy: min-length=12, complexity=on, max-age=90

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-directory-service
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Managed Microsoft AD Enterprise directory in
      us-east-1 with a two-way forest trust to onprem.example.com,
      LDAPS, and SSO. VPC vpc-aaa11122, subnets subnet-aaa111
      and subnet-bbb222."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a managed microsoft ad"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
DIRECTORY_SERVICE: d-aaa111222 (ManagedMicrosoftAD, Enterprise)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Directory type: Managed Microsoft AD
  [✓] Edition/Size: Enterprise
  [✓] VPC: vpc-aaa11122 (enableDnsSupport=true, enableDnsHostnames=true)
  [✓] Subnet AZ1: subnet-aaa111 (us-east-1a)
  [✓] Subnet AZ2: subnet-bbb222 (us-east-1b)
  [✓] DNS name: corp.example.com
  [✓] NetBIOS name: corp
  [✓] DNS conditional forwarders: configured (both sides)
  [✓] Trust relationship: Forest Two-Way to onprem.example.com
  [✓] LDAPS: enabled (cert from AWS PCA, expires 2026-12-01)
  [✓] IAM Identity Center SSO: connected
  [✓] Password policy: min-length=12, complexity=on, max-age=90
  [✓] Tags: Environment=production, ManagedBy=cloudops
VERIFICATION_COMMANDS:
  aws ds describe-directories --directory-ids d-aaa111222 --region us-east-1
  aws ds describe-trusts --directory-id d-aaa111222 --region us-east-1
  aws ds list-certificates --directory-id d-aaa111222 --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the Managed Microsoft AD directory
aws ds create-microsoft-ad \
  --name corp.example.com \
  --short-name corp \
  --password 'Adm1nP@ss!' \
  --edition Enterprise \
  --vpc-settings VpcId=vpc-aaa11122,SubnetIds=subnet-aaa111,subnet-bbb222 \
  --region us-east-1

# Step 2: Wait for the directory to become ACTIVE
aws ds describe-directories \
  --directory-ids d-aaa111222 \
  --query 'DirectoryDescriptions[0].Stage' --region us-east-1
# Expected: "Active"

# Step 3: Create conditional forwarder (AWS → on-prem)
aws ds create-conditional-forwarder \
  --directory-id d-aaa111222 \
  --remote-domain-name onprem.example.com \
  --dns-ip-addrs 10.0.1.53 10.0.2.53 \
  --region us-east-1

# Step 4: Create the two-way forest trust
aws ds create-trust \
  --directory-id d-aaa111222 \
  --remote-domain-name onprem.example.com \
  --trust-direction Two-Way \
  --trust-type Forest \
  --trust-password 'SecureTrustP@ss!' \
  --region us-east-1

# Step 5: Register LDAPS certificate
aws ds register-certificate \
  --directory-id d-aaa111222 \
  --certificate-data file://certificate.pem \
  --region us-east-1

# Step 6: Enable LDAPS
aws ds enable-ldaps \
  --directory-id d-aaa111222 \
  --type Client \
  --region us-east-1

# Step 7: Update password policy
aws ds update-password-policy \
  --directory-id d-aaa111222 \
  --min-password-length 12 \
  --require-uppercase true \
  --require-lowercase true \
  --require-numbers true \
  --require-symbols true \
  --password-history 24 \
  --max-password-age 90 \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Directory status — should be Active
aws ds describe-directories \
  --directory-ids d-aaa111222 \
  --query 'DirectoryDescriptions[0].{Stage:Stage,Type:Type,Edition:Edition,DNS:Name}' \
  --region us-east-1

# Trust status — should be Verified
aws ds describe-trusts \
  --directory-id d-aaa111222 \
  --query 'Trusts[0].{State:TrustState,Direction:TrustDirection,Type:TrustType}' \
  --region us-east-1

# LDAPS certificates
aws ds list-certificates \
  --directory-id d-aaa111222 \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Trust direction | Creates trust without considering direction semantics | Explicit One-Way vs Two-Way with direction explained | Wrong direction = silent trust failure; cannot change after creation |
| Conditional forwarders | Creates trust without DNS forwarders | Forwarders on BOTH sides before trust creation | Trust requires DNS resolution between domains first |
| LDAPS lifecycle | Enables LDAPS without monitoring expiry | Certificate lifecycle planned with CloudWatch alarm on DaysToExpiry | Certificate expiry silently breaks LDAPS |
| AD Connector limitations | Tries LDAPS or trusts on AD Connector | Only Managed AD for trusts/LDAPS | AD Connector does not support these features |
| Edition immutability | Picks Standard without considering Multi-Region | Enterprise if any chance of Multi-Region replication | Edition cannot change after creation |
| VPC DNS support | Creates directory without checking VPC DNS | Verifies enableDnsSupport and enableDnsHostnames first | Directory creation fails without VPC DNS |

---

## Related artifacts

- **Skill definition:** `skills/directory-service-deployer/SKILL.md`
- **Trust and LDAPS guide:** `skills/directory-service-deployer/references/trust-and-ldaps.md`
- **SSO and sharing guide:** `skills/directory-service-deployer/references/sso-and-sharing.md`
- **Slash command:** `commands/aws/deploy-directory-service.md`
- **Eval suite:** `skills/directory-service-deployer/evals/evals.json`
- **Legacy test cases:** `skills/directory-service-deployer/eval/test-cases.yaml`
