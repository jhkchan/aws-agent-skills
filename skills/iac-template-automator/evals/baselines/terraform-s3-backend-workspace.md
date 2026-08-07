# Baseline (no-skill) response: terraform-s3-backend-workspace

This file captures what a generic assistant produces WITHOUT the
iac-template-automator skill loaded.

---

Here's a Terraform configuration for a VPC:

```hcl
provider "aws" {
  region = "us-east-1"
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}
```

You can use the terraform-aws-modules/vpc/aws module for more
configuration options like subnets and NAT gateways. Make sure to
configure your S3 backend for state management.
