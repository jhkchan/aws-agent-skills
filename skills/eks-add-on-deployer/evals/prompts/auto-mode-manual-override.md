# Eval: auto-mode-manual-override

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — Auto Mode manages vpc-cni automatically; manual changes are silently reverted by reconciliation

## Prompt

My EKS cluster auto-mode-cluster uses EKS Auto Mode. I want to
manually update the vpc-cni add-on to version v1.19.0-eksbuild.1
and set ENABLE_IPv6 to true. Account ID: 123456789012.
