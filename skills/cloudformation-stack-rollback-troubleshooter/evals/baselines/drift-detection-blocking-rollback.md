# Baseline (no-skill) response: drift-detection-blocking-rollback

---

Your stack rollback is failing because the security group has been
modified outside of CloudFormation. Someone added an ingress rule
manually via the console. You need to remove that manual change so
the security group matches the template.

Try going into the EC2 console and removing the manually-added ingress
rule (port 5432 from 10.0.1.0/24). Then retry the rollback. You should
also fix the tag value that was changed.
