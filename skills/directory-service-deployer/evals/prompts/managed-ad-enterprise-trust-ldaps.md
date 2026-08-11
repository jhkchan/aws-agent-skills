# Eval: managed-ad-enterprise-trust-ldaps

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Managed AD Enterprise, two-way forest trust with conditional forwarders on both sides, LDAPS with AWS PCA certificate, IAM Identity Center SSO connected

## Prompt

Create a Managed Microsoft AD Enterprise directory in us-east-1.
VPC vpc-aaa11122 with subnets subnet-aaa111 (us-east-1a) and
subnet-bbb222 (us-east-1b). DNS name corp.example.com, NetBIOS
name corp. Set up a two-way forest trust with onprem.example.com
(conditional forwarders on both sides, on-prem DNS at 10.0.1.53
and 10.0.2.53). Enable LDAPS with a certificate from AWS PCA
(expiring 2026-12-01). Connect IAM Identity Center SSO. Password
policy: min-length 12, complexity on, max-age 90. Tags:
Environment=production, ManagedBy=cloudops.
