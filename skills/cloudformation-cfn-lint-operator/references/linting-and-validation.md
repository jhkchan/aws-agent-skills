# Linting and Validation — CloudFormation cfn-lint Operator

Deep reference on cfn-lint static analysis (rule categories, custom
rules, configuration files), validate-template API mechanics (what it
checks and does not check), SAM transform expansion validation, and
nested stack validation. Loaded on demand by the skill — kept out of
the main SKILL.md body so the operation procedure stays scannable.

## cfn-lint deep dive

### Rule categories

cfn-lint organizes checks into rule categories by ID prefix:

| Prefix | Category | Description |
|---|---|---|
| E | Errors | Template will fail at deploy time (e.g., E1019 invalid Ref) |
| W | Warnings | Potential issue that may cause problems |
| I | Informational | Best practice suggestions |
| N | Non-standard | Non-standard template features |

### Common error rules

| Rule ID | Description |
|---|---|
| E1011 | FindInMap resolution to non-existent map |
| E1019 | Ref to non-existent resource or parameter |
| E1029 | Sub variable does not resolve to a resource or parameter |
| E3001 | Invalid resource type |
| E3002 | Resource property is not valid for the resource type |
| E3003 | Missing required property |
| E3004 | Property value type mismatch |
| E3012 | Property has invalid value (e.g., enum constraint) |
| E3037 | DependsOn references non-existent resource |
| E3501 | Output value references non-existent resource |

### Running cfn-lint with configuration

```bash
# Use a .cfnlintrc configuration file
# Place .cfnlintrc in the project root:
# {
#   "include_checks": ["I"],
#   "exclude_checks": ["E3012"],
#   "templates": ["**/template*.yaml"]
# }
cfn-lint

# Override configuration with CLI flags
cfn-lint template.yaml --include-checks I3001,I3002 --exclude-checks E3012

# Configure via environment variable
export CFN_LINT_IGNORE_TEMPLATES="*test*"
cfn-lint template.yaml
```

### Output formats for CI/CD

```bash
# JSON output (parseable for pipeline gates)
cfn-lint template.yaml --format json > cfn-lint-results.json

# JUnit XML (for Jenkins, GitLab CI)
cfn-lint template.yaml --format junit > cfn-lint-junit.xml

# SARIF (for GitHub Code Scanning)
cfn-lint template.yaml --format sarif > cfn-lint.sarif
```

### Pipeline gate logic

```bash
# Exit code 0 = no errors; non-zero = errors found
if cfn-lint template.yaml; then
  echo "cfn-lint passed"
else
  echo "cfn-lint failed — blocking deployment"
  exit 1
fi

# Warnings do not cause non-zero exit by default.
# To treat warnings as errors:
cfn-lint template.yaml --non-zero-exit-code any
```

### Custom rules

cfn-lint supports custom rules via Python plugins:

```python
# custom_rule.py
from cfnlint.rules import CloudFormationLintRule

class NoHardcodedARNs(CloudFormationLintRule):
    id = "E9001"
    shortdesc = "No hardcoded ARNs"
    description = "Check for hardcoded ARNs in properties"
    tags = ["resources"]

    def match(self, cfn):
        matches = []
        for resource_name, resource_values in cfn.get_resources().items():
            properties = resource_values.get("Properties", {})
            for key, value in properties.items():
                if isinstance(value, str) and value.startswith("arn:aws:"):
                    if not value.startswith("arn:aws:cloudformation:"):
                        matches.append(
                            cfnlint.Match(
                                1, 1, 1, 1,
                                self,
                                f"Hardcoded ARN in {resource_name}.{key}"
                            )
                        )
        return matches
```

```bash
# Run with custom rules
cfn-lint template.yaml --custom-rules ./custom_rules/
```

## validate-template API mechanics

### What validate-template actually checks

`validate-template` calls the CloudFormation `ValidateTemplate` API.
This API:

1. Parses the template as YAML or JSON.
2. Checks basic template structure (Resources required, etc.).
3. Validates resource type names against the AWS resource
   specification.
4. Validates property names for each resource type.
5. Returns the template's parameters and outputs as a summary.

### What it does NOT check

- Property VALUE validity (e.g., it checks that `BucketName` is a
  valid property for `AWS::S3::Bucket`, but does NOT check whether
  the value follows S3 naming rules).
- Logical errors (circular dependencies, invalid conditions).
- Security anti-patterns.
- IAM policy document validity.
- Resource limits (e.g., S3 bucket name uniqueness).

### Example: validate-template passes but deploy fails

```yaml
# This template passes validate-template but fails at deploy time
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: "INVALID NAME WITH SPACES"  # validate-template does NOT check value format
```

`validate-template` passes because `BucketName` is a valid property.
But `aws cloudformation create-stack` fails because S3 bucket names
cannot contain spaces.

This is why cfn-lint (which has value-level checks like E3012) is
needed in addition to validate-template.

## SAM transform expansion validation

### Why expansion is needed

SAM templates contain `AWS::Serverless::*` resource types that do not
exist in standard CloudFormation. The `Transform:
AWS::Serverless-2016-10-31` directive tells CloudFormation to expand
these into standard resources at deployment time.

cfn-lint has PARTIAL awareness of SAM resource types — it knows the
property structure of `AWS::Serverless::Function` and
`AWS::Serverless::Api`, but it does NOT fully simulate the transform
expansion. Issues in the expanded template (e.g., auto-generated IAM
roles with overly permissive policies) are invisible to cfn-lint
without expansion.

### Expansion workflow

```bash
# Step 1: Expand the SAM template
sam translate \
  --template-file template-sam.yaml \
  --output-file template-expanded.yaml

# Step 2: Run cfn-lint on the expanded template
cfn-lint template-expanded.yaml

# Step 3: Run cfn-nag on the expanded template
# This catches security issues in auto-generated resources (IAM roles)
cfn_nag_scan --input-path template-expanded.yaml

# Step 4: Validate the expanded template
aws cloudformation validate-template \
  --template-body file://template-expanded.yaml \
  --region us-east-1
```

### Common SAM expansion issues

| Issue | cfn-lint catches (pre-expansion) | cfn-nag catches (post-expansion) |
|---|---|---|
| Missing CodeUri | YES | N/A |
| Auto-generated IAM role with wildcard | NO | YES (F1) |
| Deprecated runtime | YES | NO |
| Globals section misconfiguration | YES | N/A |
| Implicit API with no auth | NO | YES (WARNING) |

## Nested stack validation

### Parent-child template relationship

A parent template references child templates via
`AWS::CloudFormation::Stack`:

```yaml
# parent-template.yaml
Resources:
  NetworkStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://s3.amazonaws.com/my-bucket/child-network.yaml
      Parameters:
        VpcCidr: !Ref VpcCidrParam

  DatabaseStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://s3.amazonaws.com/my-bucket/child-database.yaml
      Parameters:
        DatabaseName: !Ref DbNameParam
```

### Validation procedure

Each template (parent + every child) must be validated independently:

```bash
# Validate parent
cfn-lint parent-template.yaml
aws cloudformation validate-template --template-body file://parent-template.yaml --region us-east-1

# Validate each child
for child in child-network.yaml child-database.yaml; do
  echo "Validating $child..."
  cfn-lint "$child"
  aws cloudformation validate-template --template-body "file://$child" --region us-east-1
done
```

### Common nested stack issues

1. **Parameter mismatch:** parent passes parameters the child does
   not define, or child expects parameters the parent does not pass.
   - cfn-lint catches this if both templates are in the same project
     and configured with `--template-urls`.

2. **TemplateURL points to non-existent S3 object:** only caught at
   deploy time. Verify the S3 URL is correct and accessible.

3. **Output dependency:** parent references a child's output via
   `!GetAtt ChildStack.Outputs.MyOutput` — the child MUST export that
   value. cfn-lint checks this within the same project.

4. **Circular dependencies between nested stacks:** not allowed. If
   StackA references StackB and StackB references StackA, deployment
   fails. Design a linear or tree dependency graph.

## Misconception — "validate-template is enough"

- **"validate-template is enough."** It is not. `validate-template`
  checks syntax and basic resource specification compliance against
  the CloudFormation API. It does NOT catch logical errors (e.g.,
  circular dependencies, impossible conditions), security anti-
  patterns (wildcard IAM, unencrypted resources), or cost surprises.
  cfn-lint catches structural/logical issues. cfn-nag catches
  security issues. Both are needed in addition to validate-template.
