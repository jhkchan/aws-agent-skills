# Eval: multi-volume-block-device

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — x86_64 + m5d.large, root gp3 3000, data gp3 12000 IOPS 500 MB/s, ephemeral0 instance store

## Prompt

Create a launch template for a data-processing worker on
m5d.large in us-east-1. AMI: ami-0dataworker (x86_64). Block
devices: root 50 GB gp3 3000 IOPS, data volume 500 GB gp3
12000 IOPS 500 MB/s throughput, and instance store ephemeral0
at /dev/sdb (m5d has NVMe). Key pair: data-key. Security
group: sg-0data (VPC vpc-0data). IAM profile: data-role.
Subnet: subnet-0data. IMDSv2 required hop limit 1. Tags:
Application=data-worker, Environment=production. Account:
123456789012.
