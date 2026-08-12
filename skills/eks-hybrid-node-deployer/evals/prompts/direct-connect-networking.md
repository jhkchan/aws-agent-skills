# Eval: direct-connect-networking

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Direct Connect network path to EKS API, latency requirement for kubelet heartbeats, on-prem firewall rules replace VPC security groups

## Prompt

Set up networking for EKS hybrid nodes on prod-cluster. The
on-prem data center connects to AWS via Direct Connect
(dxcon-aaa111, private VIF). EKS API endpoint is
https://XXXX.gr7.us-east-1.eks.amazonaws.com. On-prem nodes are
in 10.0.0.0/16. Configure firewall rules. us-east-1.
