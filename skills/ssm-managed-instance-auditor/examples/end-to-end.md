# End-to-end usage scenario: ssm-managed-instance-auditor

A walkthrough showing the skill auditing a fleet of three instances that
collectively exercise every verdict — UNMANAGED (silent EC2 coverage
hole), NONCOMPLIANT (managed but CRITICAL patches missing), and
NO_SESSION_MANAGER (managed and patched but SSH open to the internet) —
plus an OK instance to anchor the contrast.

## Input (user prompt)

> Audit my SSM fleet for production readiness. The compliance team is
> asking for evidence that every instance is reachable, patched, and
> not exposed via open SSH. I have four instances in scope.

Instance 1: `i-0ec2noiamprofileunmanaged` — running Linux, no IAM
instance profile attached. Not visible in `describe-instance-information`.

Instance 2: `i-0noncompliantcriticalpatches` — managed, agent Active,
associations green, but `list-compliance-items` shows 14 CRITICAL
patches missing against baseline `pb-0prodlinuxsecurity`.

Instance 3: `i-0nossessionmanagersshopen` — managed, agent Active,
associations green, patches COMPLIANT, inventory fresh. Security group
`sg-0sshexposed` allows TCP/22 from `0.0.0.0/0`. No Session Manager
sessions in the last 30 days.

Instance 4: `i-0okfullymanagedsessma` — managed, agent Active and
current, all associations succeeding, patches COMPLIANT, Session Manager
in active use with S3 + CloudWatch + KMS logging, no SSH exposed.

## Skill output

```text
INSTANCE: i-0ec2noiamprofileunmanaged
VERDICT: UNMANAGED
REASON: EC2 instance is running but has no IAM instance profile attached
(Rule C-1) — SSM Agent cannot authenticate; the instance has never
registered with SSM. No patch, session, or inventory data exists.
FINDINGS:
  - [UNMANAGED] No IAM instance profile on i-0ec2noiamprofileunmanaged;
    SSM Agent cannot register (Rule C-1)
  - [INFO] Patch / session / inventory evaluation skipped — instance is
    not reporting to SSM; downstream data would be noise
REMEDIATION:
  1. Create or reuse an instance role with AmazonSSMManagedInstanceCore:
     aws iam attach-role-policy --role-name AmazonSSMManagedInstanceCore-Role \
       --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
  2. Attach it to the instance:
     aws ec2 associate-iam-instance-profile \
       --instance-id i-0ec2noiamprofileunmanaged \
       --iam-instance-profile Name=AmazonSSMManagedInstanceCore-Role
  3. Wait 5-10 min for the agent to register, then re-run this audit —
     only then can patches, sessions, and inventory be trusted.
```

```text
INSTANCE: i-0noncompliantcriticalpatches
VERDICT: NONCOMPLIANT
REASON: Instance is reachable and associations are succeeding, but
list-compliance-items reports ComplianceStatus NON_COMPLIANT with 14
CRITICAL patches missing against pb-0prodlinuxsecurity (Rule P-1). The
AWS-ApplyPatchBaseline association is Operation=Scan — it records the
gap but does not remediate.
FINDINGS:
  - [NONCOMPLIANT] 14 CRITICAL patches missing; NON_COMPLIANT (Rule P-1)
  - [CONFIG_GAP] AWS-ApplyPatchBaseline runs Operation=Scan only — no
    automated Install path (Rule P-3)
REMEDIATION:
  1. Run a one-time Install (CONFIRM first — Windows may reboot):
     aws ssm send-command \
       --instance-ids i-0noncompliantcriticalpatches \
       --document-name "AWS-ApplyPatchBaseline" \
       --parameters "Operation=[Install]" \
       --max-errors 0 --max-concurrency 1
  2. After Install completes, re-scan and verify COMPLIANT.
  3. Convert the association to a maintenance-window Install schedule
     so CRITICAL patches stop accumulating.
```

```text
INSTANCE: i-0nossessionmanagersshopen
VERDICT: NO_SESSION_MANAGER
REASON: Instance is otherwise healthy, but security group sg-0sshexposed
allows inbound TCP/22 from 0.0.0.0/0 (Rule S-1) and there are no
Session Manager sessions (active or historical) — SSH is the de-facto
access path, weaker than Session Manager (no audit trail, no key
rotation).
FINDINGS:
  - [NO_SESSION_MANAGER] Inbound TCP/22 from 0.0.0.0/0 on sg-0sshexposed
    with no Session Manager use in last 30 days (Rule S-1)
REMEDIATION:
  1. Verify Session Manager prerequisites (agent v2.3.12.0+,
     AmazonSSMManagedInstanceCore present).
  2. Test: aws ssm start-session --target i-0nossessionmanagersshopen
  3. After verifying Session Manager works, restrict the SSH rule:
     aws ec2 revoke-security-group-ingress --group-id sg-0sshexposed \
       --protocol tcp --port 22 --cidr 0.0.0.0/0
     aws ec2 authorize-security-group-ingress --group-id sg-0sshexposed \
       --protocol tcp --port 22 --cidr <corporate-egress>/32
  4. Enable session logging (S3 + CloudWatch + KMS) for audit trail.
```

```text
INSTANCE: i-0okfullymanagedsessma
VERDICT: OK
REASON: Agent is current (v3.1.161.0) and Active, all associations
succeeding, patches COMPLIANT, Session Manager in active use with S3 +
CloudWatch + KMS logging, no SSH exposed.
FINDINGS:
  - [OK] Coverage, association, patch, session, and inventory dimensions
    all clean
REMEDIATION: None required. Re-audit weekly to catch posture drift.
```

## What the skill caught that a generic assistant misses

1. **The silent coverage gap.** A generic assistant might say "I see no
   SSM data for instance 1." The skill explains WHY: no IAM instance
   profile means the agent cannot authenticate; the instance never
   registered. It also flags the meta-finding: `describe-instance-information`
   alone cannot surface this gap — you must diff against
   `ec2 describe-instances`.

2. **Success != Compliance.** A generic assistant reads "association
   Status: Success" and assumes patches are healthy. The skill
   distinguishes association execution status from patch compliance
   state (separate APIs), and catches that Operation=Scan keeps
   compliance fresh without ever remediating.

3. **SSH alongside Session Manager is technical debt, not parity.** A
   generic assistant treats the SSH rule as one finding among many. The
   skill frames it as NO_SESSION_MANAGER: the open port is a parallel,
   weaker control, and the remediation is to verify Session Manager
   FIRST, then restrict SSH — not the other way round.

4. **Ordered aggregation.** The skill produces four verdicts in a
   consistent precedence (UNMANAGED > NONCOMPLIANT > NO_SESSION_MANAGER
   > CONFIG_GAP > OK), so the compliance team can triage by verdict
   without re-reading each finding.
