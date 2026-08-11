# Eval: missing-instance-profile

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — SSM connection requires AmazonSSMManagedInstanceCore in the instance profile; BasicEC2Role does not have it

## Prompt

Create a Cloud9 environment named broken-ide in us-east-1.
t3.medium instance, Amazon Linux 2, SSM connection mode. Subnet
subnet-aaa11122. Instance profile BasicEC2Role (does NOT include
AmazonSSMManagedInstanceCore). Auto-hibernate at 30 minutes.
Tags: Environment=test.
