# Eval prompt: terraform-wildcard-iam

Validate this existing Terraform module. Emit the standard VERDICT block
(PATTERN, TOOL, VERDICT, TEMPLATE, VALIDATION, SECURITY, FINDINGS,
REMEDIATION).

Pattern: custom (IAM role for an app)
Tool: terraform

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_iam_role" "app_role" {
  name               = "app-role"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy" "app_policy" {
  name = "app-policy"
  role = aws_iam_role.app_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "*"
        Resource = "*"
      }
    ]
  })
}
```

Expected: MANUAL_STEP_REQUIRED. The skill detects:
1. CRITICAL: IAM policy uses Action: "*" — least-privilege baseline
   (rule 2) fails.
2. CRITICAL: IAM policy uses Resource: "*" — least-privilege baseline
   (rule 2) fails.
3. Both findings must appear with specific remediation (scope to specific
   actions and resources, optionally add a permissions boundary).
