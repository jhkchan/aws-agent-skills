# End-to-end usage scenario: ssm-association-troubleshooter

A walkthrough showing the skill diagnosing two SSM association
problems in the same account: a ROOT_CAUSE_FOUND Failed
association with an S3 access-denied gap and an ESCALATE
hybrid-activation expiry. Demonstrates the 3-layer SSM health
check and the 5-symptom decision tree.

## Input (user prompt)

> Diagnose two SSM association problems: (1) prod-inventory-collect
> on i-0abc123def456789a shows Failed with AccessDenied on S3;
> (2) hybrid instance mi-0abc123def456789a disappeared from SSM.

```
Diagnosis reference: prod-ssm-triage
Account: 111111111111
Region: us-east-1

Problem 1: EC2 association Failed
  Association-id: 0123456789abcdef0123456789abcdef0123456789abcdef0
  Association name: prod-inventory-collect
  Instance-id: i-0abc123def456789a
  Symptom: Failed
  Recent output:
    describe-association-executions Status=Failed,
      StatusMessage="AccessDenied on s3:PutObject for arn:aws:s3:::ssm-output-prod/..."
    describe-instance-information: PingStatus=Active,
      AgentVersion=3.2.1555.0, IsLatestVersion=true
    simulate-principal-policy: Denied for s3:PutObject on
      arn:aws:s3:::ssm-output-prod/*

Problem 2: Hybrid instance missing from SSM
  Instance-id: mi-0abc123def456789a
  Symptom: NotManaged (instance not in SSM console)
  Recent output:
    describe-instance-information for mi-*: empty
    describe-activations: Expired=true, ExpiryDate=2026-06-01
```

## Skill output

```text
DIAGNOSIS: prod-ssm-triage (problem 1)
ASSOCIATION: 0123456789abcdef0123456789abcdef0123456789abcdef0
INSTANCE: i-0abc123def456789a
SYMPTOM: Failed
ROOT_CAUSE: Instance role lacks s3:PutObject on the S3 output
            bucket; association execution failed writing command
            output to s3://ssm-output-prod/.
EVIDENCE:
  - describe-association-executions Status=Failed, StatusMessage="AccessDenied on s3:PutObject"
  - simulate-principal-policy returned Denied for s3:PutObject on arn:aws:s3:::ssm-output-prod/*
LAYER_CHECK:
  - IAM: FAIL — instance role has AmazonSSMManagedInstanceCore but NOT s3:PutObject on ssm-output-prod
  - Connectivity: PASS — PingStatus Active within last 5 min
  - Agent: PASS — IsLatestVersion true, agent v3.2.1555.0
FIX:
  - Add an inline policy granting s3:PutObject on arn:aws:s3:::ssm-output-prod/*:
    aws iam put-role-policy --role-name <instance-role> --policy-name SsmOutputPut --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"s3:PutObject","Resource":"arn:aws:s3:::ssm-output-prod/*"}]}'
  - Re-run the association:
    aws ssm start-associations-once --association-ids 0123456789abcdef0123456789abcdef0123456789abcdef0
VERIFICATION:
  - aws ssm describe-association-executions --association-id 0123456789abcdef0123456789abcdef0123456789abcdef0 --query 'Executions[0].[Status,StatusMessage]' --output table
  - Expect: Success, no AccessDenied
VERDICT: ROOT_CAUSE_FOUND
NEXT_STEP: None
ESCALATION_PATH: None

DIAGNOSIS: prod-ssm-triage (problem 2)
ASSOCIATION: (none — instance not managed, no association can run)
INSTANCE: mi-0abc123def456789a
SYMPTOM: NotManaged
ROOT_CAUSE: Hybrid activation aabbccdd-1111-2222-3333-aabbccddeeff
            is expired (Expired: true, ExpiryDate=2026-06-01).
            The mi-* instance was registered under this activation;
            the agent can no longer re-authenticate.
EVIDENCE:
  - describe-instance-information returns nothing for mi-0abc123def456789a
  - describe-activations shows the activation Expired=true (expiry 2026-06-01)
LAYER_CHECK:
  - IAM: FAIL — activation role no longer exchangeable
  - Connectivity: unknown (instance not in SSM)
  - Agent: unknown (instance not in SSM)
FIX: Cannot remediate from AWS side alone — the on-prem host must
  re-register with a new activation code. Requires on-host access.
VERIFICATION: After re-registration:
  aws ssm describe-instance-information \
    --instance-information-filter-list Key=InstanceIds,ValueSet=mi-0abc123def456789a
  Expect: PingStatus=Active within 5-10 minutes.
VERDICT: ESCALATE
NEXT_STEP: Provide on-prem operator with a new activation code:
  aws ssm create-activation --iam-role AmazonSSMManagedInstanceCore-Role \
    --registration-limit 1 --expiry-date $(date -u -v+7d +%Y-%m-%d)
ESCALATION_PATH: On-prem / edge-device operator must run on the host:
  amazon-ssm-agent -register -code <new-code> -id <new-id> -region <region>
  (requires sudo / admin on the host). Cannot be done from the AWS side.
```

**Account-level aggregate verdict: ROOT_CAUSE_FOUND for problem 1
(fix is an inline IAM policy + re-run) and ESCALATE for problem 2
(requires on-prem operator action).**

## What the skill caught that a generic assistant misses

1. **The 3-layer health check.** A generic assistant treats each
   symptom in isolation. The skill always runs the 3-layer check
   (IAM, connectivity, agent) first — for problem 1 this confirmed
   connectivity and agent were fine, isolating the IAM gap to S3
   specifically. For problem 2, the layer check revealed the IAM
   layer failure (expired activation).

2. **The orchestration-vs-target status distinction.** A generic
   assistant treats association `Failed` as a single failure mode.
   The skill distinguishes orchestration failure (Step 2) from
   per-target document failure (Step 6) — the diagnostic paths
   diverge.

3. **The simulate-principal-policy evidence.** A generic assistant
   guesses at the IAM gap. The skill cites the
   `simulate-principal-policy` output proving `s3:PutObject` is
   Denied, then provides the exact inline policy to add.

4. **The hybrid activation diagnosis.** A generic assistant
   recommends "restarting the SSM Agent on the instance." The
   skill recognizes `mi-*` instances are hybrid activations and
   that the activation has expired — a different remediation path
   (re-registration, not agent restart). The skill ESCALATES
   because re-registration requires on-host access.

5. **The verdict shapes.** A generic assistant produces prose. The
   skill emits a deterministic VERDICT (ROOT_CAUSE_FOUND, ESCALATE)
   per problem, enabling downstream automation and clear escalation
   paths.

## Slash-command invocation

```
/aws:troubleshoot-ssm-association
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose my failing SSM association"
```

## CLI routing

```bash
node cli/bin/cli.js route "SSM association failed"
# [Phase: Troubleshoot | Skills routed: ssm-association-troubleshooter]
```

## Live-account invocation (requires AWS CLI)

```bash
# Run the 3-layer SSM health check
aws ssm describe-instance-information \
  --instance-information-filter-list Key=InstanceIds,ValueSet=<instance-id> \
  --query 'InstanceInformationList[*].[PingStatus,LastPingDateTime,AgentVersion,IsLatestVersion,PlatformType,IamRoleARN]' \
  --output table --region us-east-1 --profile default

# Verify EC2 instance profile
aws ec2 describe-instances --instance-ids <instance-id> \
  --query 'Reservations[*].Instances[*].[State.Name,IamInstanceProfile.Arn]' \
  --output text --profile default

# Check attached role policies
aws iam list-attached-role-policies --role-name <role-name> \
  --query 'AttachedPolicies[*].PolicyName' --output text --profile default

# Verify VPC endpoints (private subnet)
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=<vpc-id> \
  --query 'VpcEndpoints[?contains(ServiceName,`.ssm.`) || contains(ServiceName,`.ssmmessages.`) || contains(ServiceName,`.ec2messages.`)].[ServiceName,State]' \
  --output table --profile default

# Drill into association execution
aws ssm describe-association-executions \
  --association-id <association-id> \
  --query 'Executions[0].[ExecutionId,Status,StatusMessage,ExecutionTime]' \
  --output table --profile default

aws ssm describe-association-execution-targets \
  --association-id <association-id> \
  --execution-id <execution-id> \
  --query 'Targets[*].[Status,StatusMessage,ResourceId,OutputSource.S3Url]' \
  --output table --profile default

# Fetch the S3 output
aws s3 cp <s3-url-from-above> - --profile default

# Simulate IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn <instance-role-arn> \
  --action-names s3:PutObject \
  --resource-arns arn:aws:s3:::<output-bucket>/* \
  --query 'EvaluationResults[*].[EvalActionName,EvalDecision]' \
  --output table --profile default

# Check hybrid activations
aws ssm describe-activations \
  --filters Key=RegistrationStatus,Values=Registered \
  --query 'ActivationList[*].[ActivationId,IamRole,Expired,ExpiryDate]' \
  --output table --profile default
```

Then paste the output into the skill for diagnosis.
