# Baseline (no-skill) response: vpc-no-nat-package-install

This file captures what a generic assistant produces WITHOUT the
codebuild-build-troubleshooter skill loaded.

---

Your CodeBuild build is failing on npm install with a network timeout.
This means the build container can't reach the npm registry. Check your
network configuration — if the build is running in a VPC, make sure it
has internet access. You might need to add a NAT Gateway or configure
VPC endpoints.

Also check your security group rules to make sure outbound traffic on
port 443 is allowed. The npm registry is at registry.npmjs.org over
HTTPS, so the build needs to be able to reach the internet.
