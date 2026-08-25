# Advanced Patterns — CodeCommit Repository Deployer

Load-on-demand deep dives moved verbatim from SKILL.md.

## Mindset — three misconceptions at provisioning time

Three misconceptions dominate CodeCommit misconfiguration at provisioning
time:

- **"Creating the repository is enough to push code."** It is not. The
  default branch (e.g., `main`) does NOT exist until the first commit is
  pushed. If branch protection or approval rules are configured before
  the initial commit, the operator must push via an unprotected path
  first.

- **"KMS encryption just needs the key ARN."** It does not. CodeCommit
  must be a principal in the KMS key policy with `kms:Encrypt`,
  `kms:Decrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*`, and
  `kms:DescribeKey`. A missing key policy grant is a silent failure
  (repository creates, push/pull fails with AccessDenied).

- **"git-remote-codecommit (GRC) is the same as git credentials."** It
  is not. GRC uses the AWS signer to generate a session token from IAM
  credentials — no static credentials to rotate, no SSH keys to manage.
  GRC is the recommended auth method for federated/IAM-role-based
  environments.

## Configuration dependency graph (novel heuristic)

CodeCommit configurations are NOT independent. The repository must exist
before KMS encryption, approval rules, notification rules, triggers, and
resource policies can be attached. The default branch must exist (first
push) before branch-level protection is effective. KMS key policy must
grant CodeCommit before the repository can encrypt.

| Configuration | Hard dependencies | Silent failure | Enables downstream |
|---|---|---|---|
| Repository | AWS account in a supported region | `defaultBranchName` set at creation but branch does NOT exist until first push | the repository ARN |
| KMS encryption | KMS key exists; key policy grants CodeCommit | repo creates fine WITHOUT valid key grant; push/pull fails at encryption time | at-rest encryption |
| Default branch | repository exists; first commit pushed | branch does not exist until `git push` succeeds; approval rules have nothing to protect | branch-level protection |
| Approval rule template | repository exists; approver pool known | template must be ASSOCIATED via associate call — creating alone does nothing | required-reviewer enforcement |
| Notification rule | SNS topic exists; topic policy grants CodeStar | rule creates but no notifications fire if topic policy missing | event-driven notifications |
| Cross-account resource policy | repository exists; cross-account principal identified | resource policy grants GitPull/Push but KMS key policy must ALSO grant cross-account | cross-account Git access |
| Repository trigger | repository exists; Lambda/SNS target exists | trigger creates but never fires if target resource policy missing CodeCommit | push/PR event automation |

**The KMS-key-policy row is the one a baseline model misses.** Creating
the repository with a KMS key ID succeeds even if the key policy does
not grant CodeCommit. The failure surfaces only at push/pull time.
