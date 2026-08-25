# Diagnostic Commands (load on demand) — CodeArtifact Domain Deployer

Pre-flight and diagnostic command listings moved verbatim from SKILL.md. Load on demand.

---

## Step 1 — create a domain (default key vs CMK) (moved from SKILL.md)

```bash
# Domain with default AWS-managed encryption key
aws codeartifact create-domain \
  --domain my-domain \
  --region us-east-1

# Domain with custom KMS CMK (IMMUTABLE — cannot change later)
aws codeartifact create-domain \
  --domain my-domain \
  --encryption-key arn:aws:kms:us-east-1:123456789012:key/abcd1234-... \
  --region us-east-1
```

## Step 1 — domain permissions policy (moved from SKILL.md)

```bash
aws codeartifact put-domain-permissions-policy \
  --domain my-domain \
  --policy-document file://domain-policy.json \
  --region us-east-1
```

## Step 2 — create-repository (moved from SKILL.md)

```bash
aws codeartifact create-repository \
  --domain my-domain \
  --repository my-team-packages \
  --description "Internal npm packages for my team" \
  --region us-east-1
```

## Step 3 — set upstreams (cascade order) (moved from SKILL.md)

```bash
# Set upstreams (order matters — first match wins)
aws codeartifact update-repository \
  --domain my-domain \
  --repository my-team-packages \
  --upstreams repository=shared-team-packages \
  --upstreams repository=company-approved-packages \
  --region us-east-1
```

## Step 4 — list external connections (moved from SKILL.md)

```bash
# Check available external connections
aws codeartifact list-external-connections \
  --region us-east-1

# Common external connections:
#   npmjs         → npmjs.com
#   pypi          → pypi.org
#   mavencentral  → search.maven.org
#   nuget-org     → nuget.org
```

## Step 4 — add external connection as last upstream (moved from SKILL.md)

```bash
# Add external connection as the LAST upstream (after internal repos)
aws codeartifact update-repository \
  --domain my-domain \
  --repository my-team-packages \
  --upstreams repository=shared-team-packages \
  --upstreams external-connection=npmjs \
  --region us-east-1
```

## Step 5 — authorization token (login CLI + API token) (moved from SKILL.md)

```bash
# npm login (writes .npmrc)
aws codeartifact login \
  --tool npm \
  --domain my-domain \
  --domain-owner 123456789012 \
  --repository my-team-packages \
  --region us-east-1

# pip login (writes pip.conf under codeartifact directory)
aws codeartifact login \
  --tool pip \
  --domain my-domain \
  --domain-owner 123456789012 \
  --repository my-team-packages \
  --region us-east-1

# Alternative: generate token via API (for CI/CD)
TOKEN=$(aws codeartifact get-authorization-token \
  --domain my-domain \
  --domain-owner 123456789012 \
  --query authorizationToken --output text \
  --region us-east-1)
# Token expires in 12 hours — MUST be refreshed
```

## Step 6 — direct publish (npm) (moved from SKILL.md)

```bash
# After aws codeartifact login --tool npm ...
cd my-package/
npm publish
```

## Step 6 — copy-package-versions ingest (moved from SKILL.md)

```bash
aws codeartifact copy-package-versions \
  --domain my-domain \
  --repository my-team-packages \
  --source-repository shared-team-packages \
  --format npm \
  --namespace lodash \
  --package lodash \
  --versions 4.17.21 \
  --region us-east-1
```

## Step 7 — cross-account repository policy (moved from SKILL.md)

```bash
# Domain owner grants read access to consumer account 999999999999
aws codeartifact put-repository-permissions-policy \
  --domain my-domain \
  --repository my-team-packages \
  --policy-revision 1 \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::999999999999:root"
        },
        "Action": [
          "codeartifact:ReadFromRepository",
          "codeartifact:GetAuthorizationToken",
          "codeartifact:GetRepositoryEndpoint"
        ],
        "Resource": "*"
      }
    ]
  }' \
  --region us-east-1
```

## Step 7 — consumer account login (moved from SKILL.md)

```bash
# Consumer account gets auth token from the DOMAIN OWNER's domain
aws codeartifact login \
  --tool npm \
  --domain my-domain \
  --domain-owner 123456789012 \
  --repository my-team-packages \
  --region us-east-1
# Consumer can now npm install from the repository
```

## Step 8 — VPC interface endpoints (api + repositories) (moved from SKILL.md)

```bash
# Create VPC interface endpoint for CodeArtifact
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.codeartifact.repositories \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --security-group-ids sg-priv-1 \
  --private-dns-enabled \
  --region us-east-1

# Also create endpoint for the API (codeartifact.api)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.codeartifact.api \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --security-group-ids sg-priv-1 \
  --private-dns-enabled \
  --region us-east-1
```

## Step 9 — KMS CMK creation and encrypted domain (moved from SKILL.md)

```bash
# Create a CMK for CodeArtifact
KMS_KEY_ID=$(aws kms create-key \
  --description "CodeArtifact domain encryption key" \
  --query 'KeyMetadata.KeyId' --output text \
  --region us-east-1)

# Create domain with CMK (IMMUTABLE — cannot change later)
aws codeartifact create-domain \
  --domain my-domain \
  --encryption-key arn:aws:kms:us-east-1:123456789012:key/$KMS_KEY_ID \
  --region us-east-1
```

## Step 10 — lifecycle policy (moved from SKILL.md)

```bash
# Apply lifecycle policy (retain last 50 versions, delete older)
aws codeartifact put-lifecycle-configuration \
  --domain my-domain \
  --repository my-team-packages \
  --lifecycle-configuration '{
    "rules": [
      {
        "rulePriority": 1,
        "description": "Keep last 50 versions",
        "actions": [
          {
            "type": "retention",
            "maxVersions": 50
          }
        ]
      }
    ]
  }' \
  --region us-east-1
```

## Step 11 — CloudWatch metrics query (moved from SKILL.md)

```bash
# Monitor download/publish rates
aws cloudwatch get-metric-statistics \
  --namespace AWS/CodeArtifact \
  --metric-name PublishPackageVersion \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-11T00:00:00Z \
  --period 86400 \
  --statistics Sum \
  --dimensions Name=DomainName,Value=my-domain \
  --region us-east-1
```

