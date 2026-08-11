# Finding Types and Remediation Reference — Inspector v2 Finding Troubleshooter

Deep reference on Inspector v2 finding types (package vulnerability,
network reachability, code vulnerability), the finding JSON fields per
type, severity semantics, SBOM export integration, Lambda code
scanning, ECR image scanning, and copy-pasteable remediation commands
per layer. Loaded on demand by the skill — kept out of the main
SKILL.md body so the diagnostic procedure stays scannable.

## Finding JSON field reference

### PACKAGE_VULNERABILITY block

```json
{
  "Type": "PACKAGE_VULNERABILITY",
  "Title": "<CVE-id> on <package>",
  "Severity": "CRITICAL | HIGH | MEDIUM | LOW",
  "Description": "<CVE description from upstream advisory>",
  "Resources": [{"Type": "AWS::EC2::Instance | AWS::ECR::Repository | AWS::Lambda::Function", "Id": "<arn>"}],
  "PackageVulnerability": {
    "cve": "CVE-2024-XXXX",
    "package": "openssl",
    "vulnerableVersionRange": "< 3.0.8",
    "fixedInVersion": "3.0.8",
    "sourceUrl": "https://nvd.nist.gov/vuln/detail/CVE-2024-XXXX",
    "vendorSeverity": "HIGH"
  },
  "lastObservedAt": "2026-08-09T18:00Z",
  "updatedAt": "2026-08-09T18:00Z",
  "State": "OPEN | CLOSED | UPDATED"
}
```

### NETWORK_REACHABILITY block

```json
{
  "Type": "NETWORK_REACHABILITY",
  "Title": "<port> reachable from <scope>",
  "Severity": "CRITICAL | HIGH | MEDIUM",
  "NetworkReachability": {
    "protocol": "TCP",
    "port": 3306,
    "cidr": "0.0.0.0/0",
    "scope": "INTERNET | INTERNAL",
    "relatedIpPermissions": [{"FromPort": 3306, "ToPort": 3306, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]
  }
}
```

### CODE_VULNERABILITY block (Lambda code scanning)

```json
{
  "Type": "CODE_VULNERABILITY | LAMBDA_CODE_VULNERABILITY",
  "Title": "<rule-id>: <short description>",
  "Severity": "HIGH | MEDIUM | LOW",
  "CodeVulnerability": {
    "ruleId": "JS-HARDCODED-SECRET | JS-PATH-TRAVERSAL | JS-SQL-INJECTION",
    "filePath": "handler.js",
    "lineNumber": 42,
    "language": "JavaScript",
    "snippetText": "REDACTED"  // redacted if secret detected
  }
}
```

Use `aws inspector2 batch-get-code-snippets --finding-arns <arn>` to
fetch the snippet. Secrets are auto-redacted — use `filePath` +
`lineNumber` to locate the issue in source.

## Detailed remediation commands per layer

### EC2_OS_PACKAGE — OS package CVE

```bash
# 1. Verify the vulnerable version via SSM inventory
aws ssm list-inventory-entries --instance-id <i-id> \
  --type "AWS:Application" \
  --filters "Key=Name,Values=<package-name>" --output json

# 2. Check the fixed version is available in the patch baseline
aws ssm describe-patches \
  --filters Key=PRODUCT,Values=AmazonLinux2023 \
  --output json | jq '.[] | select(.CVEIds | contains("<cve>"))'

# 3. Apply the patched version via SSM Run Command
aws ssm send-command --instance-ids <i-id> \
  --document-name AWS-RunPatchBaseline \
  --parameters Operation=Install --output json

# 4. For targeted single-package updates
aws ssm send-command --instance-ids <i-id> \
  --document-name AWS-RunShellScript \
  --parameters commands=["dnf update -y <package-name>"]

# 5. Verify after patch completes
aws ssm list-inventory-entries --instance-id <i-id> \
  --type "AWS:Application" \
  --filters "Key=Name,Values=<package-name>" --output json
```

### ECR_BASE_IMAGE — container image CVE

```bash
# 1. Update the Dockerfile FROM directive to a patched base
# FROM <account>.dkr.ecr.<region>.amazonaws.com/base:2.0.7
# becomes
# FROM <account>.dkr.ecr.<region>.amazonaws.com/base:2.0.8

# 2. Rebuild and push
docker build -t <repo>:<new-tag> .
aws ecr get-login-password --region <region> | \
  docker login --username AWS --password-stdin \
  <account>.dkr.ecr.<region>.amazonaws.com
docker push <account>.dkr.ecr.<region>.amazonaws.com/<repo>:<new-tag>

# 3. Update the ECS task definition to reference the new image
aws ecs register-task-definition \
  --family <family> \
  --container-definitions file://task-def.json  # with new image digest

# 4. Force new deployment of the ECS service
aws ecs update-service --cluster <cluster> \
  --service <service> --force-new-deployment

# 5. Delete the old vulnerable image (after verifying no running task uses it)
aws ecr batch-delete-image --repository-name <repo> \
  --image-ids imageDigest=<old-digest>
```

### LAMBDA_LAYER — Lambda layer CVE

```bash
# 1. Identify the layer ARN from the function configuration
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '.Layers'

# 2. Rebuild the layer with patched dependencies
npm audit fix  # or: pip install --upgrade <pkg>
zip -r layer.zip nodejs/

# 3. Publish a new layer version
aws lambda publish-layer-version \
  --layer-name <layer-name> \
  --zip-file fileb://layer.zip \
  --compatible-runtimes nodejs20.x

# 4. Update every function using the layer (iterate all functions)
aws lambda list-functions --output json | \
  jq '.Functions[] | select(.Layers[]?.Arn | contains("<layer-name>")) | .FunctionName' | \
  while read fn; do
    aws lambda update-function-configuration --function-name "$fn" \
      --layers arn:aws:lambda:<region>:<account>:layer:<layer-name>:<new-ver>
  done
```

### LAMBDA_SOURCE_DEFECT — Lambda code vulnerability

```bash
# 1. Fetch the code snippet (note: secrets are REDACTED)
aws inspector2 batch-get-code-snippets --finding-arns <arn> --output json

# 2. Read the rule id and filePath to locate the source defect
aws inspector2 batch-get-finding-details --finding-arns <arn> --output json | \
  jq '.findingDetails[0].finding.codeVulnerability'

# 3. Fix the source code based on the rule:
#    - JS-HARDCODED-SECRET: load from Secrets Manager / env var
#    - JS-PATH-TRAVERSAL: validate and sanitize path input
#    - JS-SQL-INJECTION: parameterized queries
#    - JS-COMMAND-INJECTION: avoid child_process.exec with user input

# 4. Redeploy the function
aws lambda update-function-code --function-name <name> \
  --zip-file fileb://deploy.zip

# 5. If a secret was hardcoded, rotate the compromised credential
aws iam delete-access-key --access-key-id <compromised-key>
aws iam create-access-key --user-name <user>
```

### SG_OVERLY_PERMISSIVE / SG_BROAD_CIDR — reachability

```bash
# 1. Revoke the broad rule
aws ec2 revoke-security-group-ingress --group-id <sg-id> \
  --protocol tcp --port <port> --cidr 0.0.0.0/0

# 2. Add a scoped rule (referenced SG preferred over CIDR)
aws ec2 authorize-security-group-ingress --group-id <sg-id> \
  --protocol tcp --port <port> --source-security-group-id <app-sg-id>

# 3. For PUBLIC_IP_VIA_IGW, remove the public IP if not needed
aws ec2 disassociate-address --association-id <eip-assoc-id>
aws ec2 release-address --allocation-id <eip-alloc-id>
# Or move the instance to a private subnet behind an ALB/NAT gateway
```

### NO_FIX_AVAILABLE — CVE without a patch

```bash
# 1. Check upstream advisory for a config-level mitigation

# 2. Suppress if not exploitable (with documented reason)
aws inspector2 create-filter \
  --name "suppress-CVE-XXXX-not-applicable" \
  --action SUPPRESS \
  --reason "CVE conditions not met: <specific reason>" \
  --finding-criteria '{"findingCriteria":{"findingArn":[{"comparison":"EQUALS","value":"<arn>"}]}}'

# 3. Isolate the resource as defense-in-depth
aws ec2 modify-instance-attribute --instance-id <i-id> \
  --groups <isolated-sg-id>  # SG with no inbound
```

## SBOM export workflow

Inspector SBOM export (2024-2025) generates a Software Bill of
Materials for an account or resource. It augments — but does not
replace — findings.

```bash
# 1. Start an SBOM export for the account
aws inspector2 create-sbom-export \
  --report-format CYCLONEDX_1.5 \
  --s3-destination bucket=<bucket>,key=<prefix>/ \
  --resource-criteria scanResourceCriteria='{"ecrConfiguration":{"resourcetype":"AWS::ECR::Repository"}}'

# 2. Check export status
aws inspector2 list-sbom-export --output json

# 3. Download and parse the SBOM
aws s3 cp s3://<bucket>/<prefix>/<report-id>.json /tmp/sbom.json
jq '.components[] | select(.name == "<vulnerable-package>")' /tmp/sbom.json

# 4. Cross-reference with active findings
# A CVE in the SBOM that does NOT appear as an Inspector finding means
# the package is present but Inspector did not flag it (e.g., the
# version is in the safe range). Conversely, every Inspector package
# finding should appear in the SBOM.
```

SBOM formats: `CYCLONEDX_1_5` (CycloneDX 1.5) or `SPDX_3_0` (SPDX 3.0).
CycloneDX is preferred for security tooling integration.

## Code snippet redaction rules

`batch-get-code-snippets` redacts content matching secret patterns:
- AWS access keys (`AKIA...`)
- Private keys (`-----BEGIN ... PRIVATE KEY-----`)
- Bearer tokens (long base64 strings matching known patterns)
- Generic high-entropy strings (when the rule is `JS-HARDCODED-SECRET`)

When the snippet is redacted, the `filePath` and `lineNumber` fields
are NOT redacted — use them to locate the issue in source manually.
The rule id tells you the issue class even without the snippet text.

## Inspector coverage and scanning frequencies

| Resource | Default scan trigger | Scan depth |
|---|---|---|
| EC2 | Every 24h (continuous) | OS packages + SSM-managed applications |
| EC2 (deep inspection) | On enable + 24h | Application-level packages (lang ecosystems) |
| ECR | On image push | OS packages + app dependencies |
| ECR (enhanced) | On push + scheduled | Deeper CVE coverage via Inspector |
| Lambda | On function update | Deployment package + layers |
| Lambda (code scanning) | On function update | Source code SAST rules |

Use `list-coverage` to verify a resource is being scanned. Missing
coverage = no findings = false sense of security.

## Finding lifecycle

```
[OPEN] --rescan finds issue resolved--> [CLOSED] (auto)
[OPEN] --rescan still issue--> [UPDATED] (still OPEN, new lastObservedAt)
[OPEN] --operator suppression filter--> [SUPPRESSED] (manual; auditable)
```

Never manually close a finding that should auto-close on rescan — let
Inspector handle it. Use suppression only for confirmed false positives.
