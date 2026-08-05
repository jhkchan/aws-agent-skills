# Eval prompt: ec2-no-iam-profile-unmanaged

Audit the following SSM managed-instance configuration for coverage,
association compliance, patch baseline adherence, Session Manager vs SSH
exposure, and inventory collection. Emit the standard VERDICT block
(INSTANCE, VERDICT, REASON, FINDINGS, REMEDIATION).

Instance id: i-0ec2noiamprofileunmanaged
Source: describe-instance-information returned no record for this instance.
Cross-reference from ec2 describe-instances:
  InstanceId: i-0ec2noiamprofileunmanaged
  State: running
  IamInstanceProfile: (none)
  Platform: Linux

No SSM associations, patch, session, or inventory data exists for this
instance — it has never registered with SSM.

Stop at the coverage finding; do not evaluate patch/session/inventory
on an unregistered instance.
