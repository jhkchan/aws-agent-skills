# Eval: team-sharing-write

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — SSM connection, team sharing with 2 read-write + 1 read-only member, each user connects with own credentials

## Prompt

Create a Cloud9 environment named team-shared-ide in us-east-1.
t3.medium instance, Amazon Linux 2, SSM connection mode. Subnet
subnet-aaa11122. Instance profile Cloud9InstanceProfile with
AmazonSSMManagedInstanceCore. Auto-hibernate at 60 minutes.
Share with users teammate1 and teammate2 (read-write) and
reviewer1 (read-only). Tags: Environment=production, Team=dev.
