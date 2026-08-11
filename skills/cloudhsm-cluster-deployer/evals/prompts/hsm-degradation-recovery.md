# Eval: hsm-degradation-recovery

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — create replacement HSM in same cluster, wait for ACTIVE + sync, delete degraded HSM, maintain ≥2 ACTIVE HSMs

## Prompt

HSM hsm-degraded111 in CloudHSM cluster cluster-abc123def
(us-east-1a) is degraded. Walk me through the recovery procedure:
create a replacement, sync, then delete the degraded HSM. Maintain
≥2 ACTIVE HSMs in different AZs.
