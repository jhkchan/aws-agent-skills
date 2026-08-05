# Baseline (no-skill) response: ec2-no-iam-profile-unmanaged

This file captures what a generic assistant produces WITHOUT the
ssm-managed-instance-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, ordered classification,
expert reasoning about coverage gaps and IAM profiles).

---

This EC2 instance (`i-0ec2noiamprofileunmanaged`) is running but has no
IAM instance profile attached, so the SSM Agent cannot authenticate to
the Systems Manager service. It does not appear in
`describe-instance-information` because it has never registered.

You should attach an IAM role that includes the
`AmazonSSMManagedInstanceCore` policy. Once attached, the SSM Agent
should check in within about 5 minutes and the instance will appear in
SSM.

There is no patch, session, or inventory data to evaluate for this
instance yet.
