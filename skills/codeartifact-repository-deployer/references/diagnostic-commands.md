# Diagnostic Commands (load on demand) — CodeArtifact Repository Deployer

Pre-flight and diagnostic command listings moved verbatim from SKILL.md. Load on demand.

---

## Step 1 — create (or reuse) the domain (moved from SKILL.md)

```bash
aws codeartifact create-domain \
  --domain shared \
  --encryption-key arn:aws:kms:us-east-1:123456789012:key/<cmk-id>  # optional
```

## Step 2 — create the repository (moved from SKILL.md)

```bash
aws codeartifact create-repository \
  --domain shared \
  --repository shared-npm \
  --description "Shared npm packages with npmjs public upstream" \
  --tags '[{"Key":"Environment","Value":"production"},{"Key":"Format","Value":"npm"}]'
```

## Step 3 — associate external connection (moved from SKILL.md)

```bash
aws codeartifact associate-external-connection \
  --domain shared \
  --repository shared-npm \
  --external-connection public:npmjs
```

## Step 4 — configure upstreams (single upstream) (moved from SKILL.md)

```bash
# shared-npm points at shared-internal (a curated internal mirror)
# which in turn points at the public:npmjs external connection
aws codeartifact update-repository \
  --domain shared \
  --repository shared-npm \
  --upstreams repository=shared-internal
```

## Step 4 — multi-hop upstream chain (moved from SKILL.md)

```bash
aws codeartifact update-repository \
  --domain shared \
  --repository team-payments-npm \
  --upstreams repository=team-payments-internal,repository=shared-npm
```

## Step 5 — repository IAM policy JSON patterns (moved from SKILL.md)

**Domain owner admin policy (apply to a DevOps admin role):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DomainAdmin",
      "Effect": "Allow",
      "Action": ["codeartifact:*"],
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:domain/shared"
    },
    {
      "Sid": "RepositoryAdmin",
      "Effect": "Allow",
      "Action": ["codeartifact:*"],
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:repository/shared/*"
    }
  ]
}
```

**CI build consume policy (apply to a CI role):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Login",
      "Effect": "Allow",
      "Action": ["codeartifact:GetAuthorizationToken", "codeartifact:ReadFromRepository"],
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:domain/shared"
    },
    {
      "Sid": "ReadPackages",
      "Effect": "Allow",
      "Action": [
        "codeartifact:ReadFromRepository",
        "codeartifact:GetPackageVersionAsset",
        "codeartifact:ListPackageVersionAssets",
        "codeartifact:DescribePackageVersion"
      ],
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:repository/shared/shared-npm/*"
    }
  ]
}
```

**Release pipeline publish policy (apply to a release role):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Publish",
      "Effect": "Allow",
      "Action": [
        "codeartifact:PublishPackageVersion",
        "codeartifact:PutPackageMetadata",
        "codeartifact:UpdatePackageVersionsStatus",
        "codeartifact:ReadFromRepository"
      ],
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:repository/shared/shared-npm/*"
    }
  ]
}
```

## Step 6 — login CLI per format (npm, pip, maven, nuget) (moved from SKILL.md)

**npm:**

```bash
aws codeartifact login \
  --tool npm \
  --domain shared \
  --domain-owner 123456789012 \
  --repository shared-npm

# Updates ~/.npmrc with:
# registry=https://shared-123456789012.d.codeartifact.us-east-1.amazonaws.com/npm/shared-npm/
# always-auth=true
# //shared-123456789012.d.codeartifact.us-east-1.amazonaws.com/npm/shared-npm/:_authToken=<token>
```

**pip:**

```bash
aws codeartifact login \
  --tool pip \
  --domain shared \
  --domain-owner 123456789012 \
  --repository shared-pip

# Configures pip index-url in ~/.config/pip/pip.conf or ~/.pip/pip.conf
```

**maven:**

```bash
aws codeartifact login \
  --tool mvn \
  --domain shared \
  --domain-owner 123456789012 \
  --repository shared-maven

# Updates ~/.m2/settings.xml with <server> credentials and mirror config
```

**nuget:**

```bash
aws codeartifact login \
  --tool nuget \
  --domain shared \
  --domain-owner 123456789012 \
  --repository shared-nuget

# Adds a package source to nuget.config
```

## Step 7 — domain permissions policy (cross-account) (moved from SKILL.md)

```bash
# Owner account — attach a domain permissions policy
cat > /tmp/domain-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ConsumerAccountRead",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<consumer-account-id>:root"
      },
      "Action": [
        "codeartifact:DescribeDomain",
        "codeartifact:DescribeRepository",
        "codeartifact:GetAuthorizationToken",
        "codeartifact:ReadFromRepository",
        "codeartifact:ListRepositoriesInDomain"
      ],
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:domain/shared"
    }
  ]
}
EOF

aws codeartifact put-domain-permissions-policy \
  --domain shared \
  --domain-owner 123456789012 \
  --policy-revision <current-revision> \
  --policy-document file:///tmp/domain-policy.json
```

## Step 7 — RAM resource share (moved from SKILL.md)

```bash
aws ram create-resource-share \
  --name codeartifact-shared-domain \
  --principals arn:aws:iam::<consumer-account-id>:root \
  --resource-arns arn:aws:codeartifact:us-east-1:123456789012:domain/shared
```

## Step 8 — package ingestion via copy-package-versions (moved from SKILL.md)

```bash
aws codeartifact copy-package-versions \
  --domain shared \
  --repository shared-npm \
  --source-repository shared-upstream-mirror \
  --format npm \
  --package lodash \
  --versions 4.17.21
```

## Step 10 — tag, verify, and smoke-test the login (moved from SKILL.md)

```bash
aws codeartifact list-repositories-in-domain --domain shared
aws codeartifact describe-repository --domain shared --repository shared-npm
aws codeartifact get-repository-endpoint \
  --domain shared --repository shared-npm --format npm
aws codeartifact list-packages --domain shared --repository shared-npm

# Smoke test: login and install a package
aws codeartifact login --tool npm \
  --domain shared --domain-owner 123456789012 --repository shared-npm
npm install lodash
```

## Pre-flight safety checks (run before any provisioning CLI) (moved from SKILL.md)

- **Confirm the domain owner account ID:**
  `aws sts get-caller-identity --query Account --output text`
- **Confirm the domain exists or is being created:**
  `aws codeartifact describe-domain --domain <name>` (or create in
  the same stack).
- **Confirm external connections available in the Region:**
  `aws codeartifact list-external-connections --domain <name>`
- **Confirm the CI role exists:**
  `aws iam get-role --role-name ci-build`
- **For cross-account:** confirm the consumer account ID and that the
  consumer account root is referenced in the domain permissions policy.
- **For VPC endpoints:** confirm `codeartifact.api` and
  `codeartifact.repositories` endpoints exist in the VPC.
- **For KMS-encrypted domains:** confirm the CMK policy grants
  CodeArtifact service access.

