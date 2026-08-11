# Eval prompt: vpc-no-nat-package-install

Diagnose the CodeBuild build failure for the following project. Walk
the phase-status-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE,
REMEDIATION).

Symptom: project `cb-backend-api` fails in the INSTALL phase when
running `npm install`. The error is "npm ERR! network request failed"
for `registry.npmjs.org`. The project is VPC-attached in a private
subnet with no route to a NAT Gateway.

```text
ProjectName: cb-backend-api
BuildId: cb-backend-api:jkl23456
Environment:
  Image: aws/codebuild/amazonlinux2-x86_64-standard:5.0
  PrivilegedMode: false
VpcConfig:
  VpcId: vpc-0abc123
  Subnets: [subnet-private-a, subnet-private-b]
  SecurityGroupIds: [sg-codebuild]
Subnet context:
  subnet-private-a: CIDR 10.0.10.0/24, route table has no
    NAT Gateway route, no 0.0.0.0/0 route
  subnet-private-b: CIDR 10.0.11.0/24, route table has no
    NAT Gateway route, no 0.0.0.0/0 route
SG sg-codebuild egress: 0.0.0.0/0 port 443 (egress allows HTTPS)
VPC endpoints: S3 gateway only (no interface endpoints for npm)

Buildspec:
  version: 0.2
  phases:
    install:
      runtime-versions:
        nodejs: 20
      commands:
        - npm install
Phase details:
  phaseType: INSTALL
  phaseStatus: FAILED

Recent log pattern:
  npm ERR! code ETIMEDOUT
  npm ERR! network request to https://registry.npmjs.org/ failed
  npm ERR! network This is a problem related to network connectivity.
```

The security group egress allows HTTPS (443) to any destination, so
the SG is not the issue. The route table has no NAT Gateway route.
Distinguish between SG blocking and route table egress.
