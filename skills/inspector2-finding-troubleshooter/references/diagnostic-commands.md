# Diagnostic Commands — Inspector v2 Probes (all read-only)

Read-only probe commands per diagnostic step, moved verbatim from
SKILL.md for progressive disclosure. State-changing remediation
commands live in `remediation-cli-commands.md`.

## Pre-flight — account-wide commands

```bash
# 1. Get the finding JSON (the single highest-signal command)
aws inspector2 batch-get-finding-details --finding-arns <arn> --output json
# Fields: Type, Severity, Title, Resources, PackageVulnerability{cve,
#   package, vulnerableVersionRange, fixedInVersion},
#   NetworkReachability{protocol, port, cidr}, CodeVulnerability{filePath,
#   lineNumber, snippet}

# 2. Coverage + staleness (is the resource scanned? is the finding current?)
aws inspector2 list-coverage \
  --filter-criteria "ResourceArn=[{Comparison=EQUALS,Value=<arn>}]" --output json
aws inspector2 list-findings \
  --filter-criteria "FindingArn=[{Comparison=EQUALS,Value=<arn>}]" \
  --query 'findings[0].{State:State,LastObservedAt:lastObservedAt}' --output json

# 3. Code snippet for code-vulnerability findings (highest-signal for Step 4)
aws inspector2 batch-get-code-snippets --finding-arns <arn> --output json

# 4. SBOM export status (if SBOM integration is configured)
aws inspector2 list-sbom-export --output json
```

## Step 1b — full finding JSON when the type is ambiguous

```bash
aws inspector2 batch-get-finding-details --finding-arns <arn> --output json
```

## Step 2a — package CVE on EC2 instance

```bash
# SSM-managed instance inventory (the highest-signal probe)
aws ssm list-inventory-entries --instance-id <i-id> \
  --type "AWS:Application" \
  --filters "Key=Name,Values=<package-name>" --output json
# Verify the patched version is available in the baseline
aws ssm describe-patches --filters Key=PRODUCT,Values=AmazonLinux2023 \
  --output json | jq '.[] | select(.CVEIds | contains("<cve>"))'
# Check compliance state (is the instance already patched?)
aws ssm describe-instance-patches --instance-id <i-id> \
  --filters Key=STATE,Values=Installed --output json | \
  jq '.[] | select(.Title | contains("<package>"))'
```

## Step 2b — package CVE on ECR image

```bash
aws ecr describe-image-scan-findings --repository-name <repo> \
  --image-id imageDigest=<digest> --output json
aws ecr describe-images --repository-name <repo> \
  --image-ids imageDigest=<digest> --output json
# List all repo images (find other vulnerable tags)
aws ecr describe-images --repository-name <repo> --output json | \
  jq '.imageDetails[] | select(.imageTags != null)'
```

## Step 2c — package CVE on Lambda function

```bash
aws lambda get-function-configuration --function-name <name> --output json
# Look for: Runtime, Layers (ARNs), Handler, LastModified
aws lambda get-layer-version --layer-name <layer-name> \
  --version-number <n> --output json
# Download the function code package to inspect dependencies
aws lambda get-function --function-name <name> \
  --query 'Code.Location' --output text
```

## Step 3a — SG rule exposes the flagged port

```bash
aws ec2 describe-instances --instance-ids <i-id> --output json | \
  jq '.Reservations[0].Instances[0].SecurityGroups[].GroupId'
aws ec2 describe-security-groups --group-ids <sg-id> --output json | \
  jq '.SecurityGroups[].IpPermissions[]'
# The finding's NetworkReachability block names the flagged port + CIDR
aws inspector2 batch-get-finding-details --finding-arns <arn> --output json | \
  jq '.findingDetails[0].finding.networkReachability'
```

## Step 3b — IGW route exposes the resource publicly

```bash
aws ec2 describe-network-interfaces \
  --filters Name=attachment.instance-id,Values=<i-id> \
  --output json | jq '.NetworkInterfaces[].Association'
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=<subnet-id> \
  --output json | jq '.RouteTables[].Routes[]'
```

## Step 4 — Lambda code vulnerability

```bash
# Code snippet (the single highest-signal probe for code findings)
aws inspector2 batch-get-code-snippets --finding-arns <arn> --output json
# Look for: filePath, lineNumber, text (may be REDACTED)

# Lambda function configuration (handler, runtime, last modified)
aws lambda get-function-configuration \
  --function-name <name> --output json

# If the snippet is redacted, use the filePath + lineNumber from the finding
# to locate the issue in the source
aws inspector2 batch-get-finding-details --finding-arns <arn> --output json | \
  jq '.findingDetails[0].finding.codeVulnerability'
```

## Step 5 — SBOM export integration

```bash
# List SBOM export reports
aws inspector2 list-sbom-export --output json

# Get a specific SBOM export (includes S3 location, format, status)
aws inspector2 get-sbom-export --report-id <id> --output json

# Download the SBOM from S3 (CycloneDX or SPDX format)
aws s3 cp s3://<bucket>/<key> /tmp/sbom.json
# Parse for the vulnerable package across all resources
jq '.components[] | select(.name == "<package>")' /tmp/sbom.json
```

## Step 6 — staleness check (finding already fixed)

```bash
# Finding state and last-observed time
aws inspector2 list-findings \
  --filter-criteria "FindingArn=[{Comparison=EQUALS,Value=<arn>}]" \
  --query 'findings[0].{State:State,LastObservedAt:lastObservedAt}' \
  --output json

# For EC2: current package version via SSM
aws ssm list-inventory-entries --instance-id <i-id> \
  --type "AWS:Application" \
  --filters "Key=Name,Values=<package>" --output json
```
