# Eval: simple-ad-basic

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Simple AD Large with SSO, Simple AD limitations (no trust, no LDAPS, no schema extensions) noted

## Prompt

Create a Simple AD Large directory in us-east-1. VPC vpc-eee55566
with subnets subnet-eee555 (us-east-1a) and subnet-fff666
(us-east-1b). DNS name internal.example.com, NetBIOS name internal.
Connect IAM Identity Center SSO. Tags: Environment=dev,
ManagedBy=cloudops.
