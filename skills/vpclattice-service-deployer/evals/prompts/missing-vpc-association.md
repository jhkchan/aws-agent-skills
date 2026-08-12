# Eval: missing-vpc-association

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — VPC vpc-ccc33333 is NOT associated with service network sni-aaa111; instances cannot resolve Lattice DNS or reach services

## Prompt

Create a Lattice service payments-svc on service network
prod-network (sni-aaa111). VPC vpc-ccc33333 needs to access the
service. The VPC is NOT currently associated with the service
network. us-east-1.
