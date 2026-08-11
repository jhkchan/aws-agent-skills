# Eval: missing-vpc-dns-support

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — VPC vpc-nodns does not have enableDnsSupport enabled; directory creation would fail

## Prompt

Create a Managed Microsoft AD Standard directory in us-east-1.
VPC vpc-nodns with subnets subnet-ggg777 (us-east-1a) and
subnet-hhh888 (us-east-1b). The VPC does NOT have
enableDnsSupport enabled. DNS name corp.example.com, NetBIOS
name corp.
