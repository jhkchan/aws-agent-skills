# Eval: missing-trust-anchor-ca

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — no CA certificate provided (no trust anchor can be created), IAM role RolesAnywhereCIRunner lacks rolesanywhere.amazonaws.com trust policy principal

## Prompt

Create a Roles Anywhere profile in us-east-1 account
123456789012. I do not have a CA certificate yet but I want to
map certificates to role
arn:aws:iam::123456789012:role/RolesAnywhereCIRunner. The role
RolesAnywhereCIRunner currently has a trust policy that only
allows ec2.amazonaws.com (no rolesanywhere.amazonaws.com
principal). Session duration 3600 seconds. Region us-east-1.
