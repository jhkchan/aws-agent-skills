# Eval: resource-set-type-mapping

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — correct resource type mapping for NLB, Aurora cluster, and DynamoDB table with readiness checks per set

## Prompt

Create ARC readiness checks for my application. Cell-A in
us-east-1, Cell-B in us-west-2. Recovery cluster
app-cluster-2. I need readiness checks for these resource
types: NLB (AWS::ElasticLoadBalancingV2::LoadBalancer), Aurora
cluster (AWS::RDS::DBCluster), and DynamoDB table
(AWS::DynamoDB::Table). Active-standby topology. Safety rule to
prevent total outage. Tags: Application=multi-tier.
