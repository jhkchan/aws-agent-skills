# End-to-end usage scenario: ssm-session-manager-troubleshooter

A walkthrough showing the skill diagnosing two SSM Session Manager
problems in the same account: a ROOT_CAUSE_FOUND SessionFailsToStart
with an IAM document-resource gap and an ESCALATE cross-account KMS
key policy issue. Demonstrates the 4-layer Session Manager health
check and the 7-symptom decision tree.

## Input (user prompt)

> Diagnose two SSM Session Manager problems: (1) start-session on
> i-0abc123def456789a returns AccessDeniedException; (2) cross-account
> session from account 111111111111 to account 222222222222 fails
> on kms:GenerateDataKey.

```
Diagnosis reference: prod-session-triage
Account: 111111111111
Region: us-east-1

Problem 1: Session fails to start (same account)
  Instance-id: i-0abc123def456789a
  Symptom: SessionFailsToStart (AccessDeniedException)
  Recent output:
    aws ssm start-session returned:
      "AccessDeniedException: User arn:aws:sts::111111111111:assumed-role/DevOpsRole/jacky
      is not authorized to perform: ssm:StartSession"
    session-manager-plugin --version: 1.2.612.0
    describe-instance-information: PingStatus=Active,
      AgentVersion=3.3.131.0, IsLatestVersion=true
    simulate-principal-policy: Denied for ssm:StartSession on
      arn:aws:ssm:us-east-1:111111111111:document/SSM-SessionManagerRunShell
    ec2 describe-vpc-endpoints: ssm, ssmmesages, ec2messages present

Problem 2: Cross-account session fails
  Source account: 111111111111
  Target account: 222222222222
  Instance-id: i-0ddd444eee555fff6 (in target account)
  KMS key: arn:aws:kms:us-east-1:222222222222:key/abc123def456
  Symptom: LatestFeature (cross-account)
  Recent output:
    aws ssm start-session from source returned:
      "AccessDeniedException: kms:GenerateDataKey on
      arn:aws:kms:us-east-1:222222222222:key/abc123def456"
    aws kms get-key-policy: Principal =
      {"AWS":"arn:aws:iam::222222222222:root"} only
```

## Skill output

```text
DIAGNOSIS: prod-session-triage (problem 1)
INSTANCE: i-0abc123def456789a
SESSION: none - not started
SYMPTOM: SessionFailsToStart
ROOT_CAUSE: Caller identity policy scopes ssm:StartSession to
            instance resources only, omitting the
            SSM-SessionManagerRunShell document resource.
EVIDENCE:
  - aws ssm start-session returned: AccessDeniedException ... ssm:StartSession
  - simulate-principal-policy: Denied for ssm:StartSession on arn:aws:ssm:us-east-1:111111111111:document/SSM-SessionManagerRunShell
LAYER_CHECK:
  - Client: PASS - session-manager-plugin 1.2.612.0
  - IAM: FAIL - caller identity policy omits SSM-SessionManagerRunShell document resource
  - Connectivity: PASS - PingStatus Active, ssmmesages endpoint present
  - Agent: PASS - AgentVersion 3.3.131.0, IsLatestVersion true
FIX:
  - Add the session document to the caller identity policy:
    aws iam put-role-policy --role-name DevOpsRole --policy-name SsmSessionStart --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["ssm:StartSession"],"Resource":["arn:aws:ssm:us-east-1:111111111111:instance/*","arn:aws:ssm:us-east-1:111111111111:document/SSM-SessionManagerRunShell"]}]}'
  - Re-run:
    aws ssm start-session --target i-0abc123def456789a --region us-east-1 --profile default
VERIFICATION:
  - aws iam simulate-principal-policy --policy-source-arn arn:aws:sts::111111111111:assumed-role/DevOpsRole/jacky --action-names ssm:StartSession --resource-arns arn:aws:ssm:us-east-1:111111111111:document/SSM-SessionManagerRunShell --query 'EvaluationResults[0].EvalDecision' --output text
  - Expect: allowed
VERDICT: ROOT_CAUSE_FOUND
NEXT_STEP: None
ESCALATION_PATH: None

DIAGNOSIS: prod-session-triage (problem 2)
INSTANCE: i-0ddd444eee555fff6 (in account 222222222222)
SESSION: none - not started
SYMPTOM: LatestFeature (cross-account)
ROOT_CAUSE: KMS key arn:aws:kms:us-east-1:222222222222:key/abc123def456
            in the target account does not grant the source-account
            caller kms:GenerateDataKey. The key policy allows only
            the target account root.
EVIDENCE:
  - aws ssm start-session returned: AccessDeniedException ... kms:GenerateDataKey on arn:aws:kms:us-east-1:222222222222:key/abc123def456
  - aws kms get-key-policy: Statement Principal = {"AWS":"arn:aws:iam::222222222222:root"} only
LAYER_CHECK:
  - Client: PASS - session-manager-plugin 1.2.612.0
  - IAM: PASS - source-account caller has ssm:StartSession via the cross-account role
  - Connectivity: PASS - ssmmesages endpoint present in target VPC
  - Agent: PASS - AgentVersion 3.3.131.0
FIX: Cannot remediate from the source account alone - the KMS key
  policy must be modified in the target account.
VERIFICATION: After key policy update:
  aws kms describe-key --key-id arn:aws:kms:us-east-1:222222222222:key/abc123def456 --query 'KeyMetadata.KeyState' --output text --profile target-account-admin
  Expect: Enabled. Then re-run start-session from the source account.
VERDICT: ESCALATE
NEXT_STEP: Provide the target-account key admin with this statement:
  {
    "Sid": "AllowSourceAccountSessionManager",
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
    "Action": ["kms:GenerateDataKey", "kms:Decrypt"],
    "Resource": "*"
  }
ESCALATION_PATH: Target-account KMS key administrator must update the
  key policy on arn:aws:kms:us-east-1:222222222222:key/abc123def456.
  This cannot be done from the source account.
```

**Account-level aggregate verdict: ROOT_CAUSE_FOUND for problem 1
(inline IAM policy + re-run) and ESCALATE for problem 2 (requires
target-account KMS key admin).**

## What the skill caught that a generic assistant misses

1. **The 4-layer health check.** A generic assistant treats each
   symptom in isolation. The skill always runs the 4-layer check
   (client, IAM, connectivity, agent) first - for problem 1 this
   isolated the IAM gap to the document resource specifically
   (the instance resource was already granted). For problem 2, the
   layer check confirmed the failure was KMS, not connectivity.

2. **The `SSM-SessionManagerRunShell` document resource.** A
   generic assistant says "add `ssm:StartSession`." The skill
   notes that `ssm:StartSession` must be allowed on BOTH the
   instance resource AND the session document - and provides the
   exact policy snippet to fix it.

3. **The cross-account KMS-vs-IAM distinction.** A generic
   assistant conflates IAM and KMS. The skill recognizes that
   same-account sessions rely on the caller identity policy,
   while cross-account sessions also exercise the KMS key policy -
   and that the KMS key policy is the more common gap.

4. **The ESCALATE verdict.** A generic assistant attempts a
   remediation that cannot work from the source account. The skill
   ESCALATES because the KMS key policy modification requires
   target-account key admin access.

5. **The verdict shapes.** A generic assistant produces prose. The
   skill emits a deterministic VERDICT (ROOT_CAUSE_FOUND, ESCALATE)
   per problem, enabling downstream automation.

## Slash-command invocation

```
/aws:troubleshoot-ssm-session-manager
```

Or via the orchestrator:

```
/aws:pipeline
You: "why won't my Session Manager session start"
```

## CLI routing

```bash
node cli/bin/cli.js route "SSM session fails to start"
# [Phase: Troubleshoot | Skills routed: ssm-session-manager-troubleshooter]
```

## Live-account invocation (requires AWS CLI)

```bash
# Run the 4-layer Session Manager health check
session-manager-plugin --version
aws sts get-caller-identity --query 'Arn' --output text --profile default

aws ssm describe-instance-information \
  --instance-information-filter-list Key=InstanceIds,ValueSet=<instance-id> \
  --query 'InstanceInformationList[*].[PingStatus,LastPingDateTime,AgentVersion,IsLatestVersion,PlatformType]' \
  --output table --region us-east-1 --profile default

aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=<vpc-id> \
  --query 'VpcEndpoints[?contains(ServiceName,`.ssm.`) || contains(ServiceName,`.ssmmessages.`) || contains(ServiceName,`.ec2messages.`)].[ServiceName,State,PrivateDnsEnabled]' \
  --output table --profile default

# Verify caller IAM
aws iam simulate-principal-policy \
  --policy-source-arn <caller-arn> \
  --action-names ssm:StartSession \
  --resource-arns "arn:aws:ssm:us-east-1:<account>:instance/<instance-id>" "arn:aws:ssm:us-east-1:<account>:document/SSM-SessionManagerRunShell" \
  --query 'EvaluationResults[*].[EvalActionName,EvalDecision]' \
  --output table --profile default

# Inspect session history
aws ssm describe-sessions --state Terminated \
  --instance-id <instance-id> \
  --query 'Sessions[*].[SessionId,StartDate,EndDate,Duration,TerminateReason]' \
  --output table --profile default

# Cross-account KMS key policy
aws kms get-key-policy --key-id <key-id> --policy-name default --output text --profile target-account-admin

# Probe local port before binding (port forwarding)
lsof -i :<local-port-number>
```

Then paste the output into the skill for diagnosis.
