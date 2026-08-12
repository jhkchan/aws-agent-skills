# ECR Authentication and Policy Reference Guide

Supplementary reference for the ECR Push/Pull Troubleshooter skill.
Loaded on-demand when a diagnostic needs token lifecycle details,
IAM-vs-repository-policy interaction, or the full action matrix for
push and pull operations.

## Authorization token lifecycle

The ECR authorization token is the credential docker uses to
authenticate push and pull operations. Understanding its lifecycle
is essential for diagnosing AUTH_TOKEN_EXPIRED.

### Token format

The token is `base64(username:password)`:

- **username**: the literal string `AWS`
- **password**: a pre-signed STS-style URL query string containing the
  caller's access key signature, the registry hostname, and an
  `X-amz-expires=43200` parameter (12 hours).

`aws ecr get-authorization-token` returns the base64-encoded token.
`aws ecr get-login-password` returns the decoded password directly
(for piping into `docker login --password-stdin`).

### Token scope

| Scope | Behaviour |
|---|---|
| Per-registry | A token is valid for ONE registry only: `<account>.dkr.ecr.<region>.amazonaws.com`. |
| All repositories in the registry | The token authorises push/pull to every repository in that registry. There is no per-repository login. |
| Cross-region | A token for us-east-1 does NOT work for eu-west-1. Each region is a separate registry. |
| Cross-account | A token for account A does NOT work for account B. Each account has its own registry per region. |
| ECR Public vs Private | `public.ecr.aws` is a separate registry from `<account>.dkr.ecr.<region>.amazonaws.com`. A separate login is needed. |

### Token expiry

| Property | Value |
|---|---|
| Validity | 12 hours from issue (`X-amz-expires=43200`) |
| Refresh | Manual — caller must re-run `get-authorization-token` / `get-login-password` |
| Docker cache | `~/.docker/config.json` stores the token indefinitely; docker does NOT auto-refresh |
| CI guidance | Run `get-login-password` immediately before every push; never cache `~/.docker/config.json` across jobs |

### Token retrieval permissions

| API | Required IAM permission | Resource scope |
|---|---|---|
| `ecr:GetAuthorizationToken` | `ecr:GetAuthorizationToken` | `*` (service-wide; cannot be scoped to a repository) |
| `ecr-public:GetAuthorizationToken` | `ecr-public:GetAuthorizationToken` | `*` (for ECR Public) |

An SCP or permissions boundary that denies `ecr:*` on `*` breaks token
retrieval. Add an explicit `Allow` for `ecr:GetAuthorizationToken` on
`*` before any narrower deny.

## IAM identity-based policy: action matrix

### Push (docker push / docker push to ECR)

| Action | Purpose |
|---|---|
| `ecr:GetAuthorizationToken` | Retrieve the auth token (on `*`) |
| `ecr:BatchCheckLayerAvailability` | Check which layers already exist (avoid re-upload) |
| `ecr:InitiateLayerUpload` | Start a layer upload |
| `ecr:UploadLayerPart` | Upload each layer part |
| `ecr:CompleteLayerUpload` | Finalise a layer upload |
| `ecr:PutImage` | Register the image manifest with a tag |

Minimum managed policy: `AmazonEC2ContainerRegistryPowerUser`.

### Pull (docker pull / ECS task / Lambda container)

| Action | Purpose |
|---|---|
| `ecr:GetAuthorizationToken` | Retrieve the auth token (on `*`) |
| `ecr:BatchGetImage` | Fetch the image manifest(s) |
| `ecr:GetDownloadUrlForLayer` | Get a pre-signed URL for each layer download |

Minimum managed policy: `AmazonEC2ContainerRegistryReadOnly`.

### Resource scope

IAM policies for `ecr:*Image`, `ecr:*Layer*`, and `ecr:BatchCheckLayerAvailability`
can be scoped to a specific repository ARN:

```
arn:aws:ecr:<region>:<account>:repository/<repo-name>
```

`ecr:GetAuthorizationToken` CANNOT be scoped — it is always on `*`.

## Repository resource-based policy

### Same-account access

A same-account caller does NOT need a repository policy. The default
behaviour is IAM-only for same-account: if the caller's IAM policy
allows the action on the repository ARN, access is granted. A
repository policy is optional for same-account.

### Cross-account access

A cross-account caller needs BOTH:

1. The caller's IAM identity-based policy allowing the action on the
   target repository ARN.
2. The target repository's resource-based policy listing the caller's
   account (`aws:PrincipalAccount`) or ARN.

If EITHER side is missing, the pull/push fails with `denied`.

### Sample cross-account repository policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "CrossAccountPull",
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::<caller-account>:root"},
    "Action": [
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchCheckLayerAvailability"
    ]
  }]
}
```

Using `root` as the principal grants access to all principals in the
caller account that also have IAM permission. For tighter scope, list
a specific role ARN.

### Policy evaluation precedence

| Source | Effect |
|---|---|
| Explicit `Deny` in any policy (IAM, repository, SCP, permissions boundary, session policy) | Always wins — access denied |
| Explicit `Allow` in IAM + implicit allow (no deny) in repository policy (same-account) | Access granted |
| Explicit `Allow` in IAM + no repository policy (same-account) | Access granted (default same-account behaviour) |
| Explicit `Allow` in IAM + no repository policy (cross-account) | Access DENIED (repository policy required) |
| Explicit `Allow` in IAM + explicit `Allow` in repository policy (cross-account) | Access granted |
| No matching `Allow` in IAM | Access DENIED (implicit deny) |

## CloudTrail events for ECR diagnosis

| EventName | Meaning |
|---|---|
| `GetAuthorizationToken` | Caller retrieved an auth token |
| `BatchCheckLayerAvailability` | Pusher checked existing layers |
| `PutImage` | Pusher registered an image manifest with a tag |
| `BatchGetImage` | Puller fetched image manifests |
| `GetDownloadUrlForLayer` | Puller got layer download URLs |
| `BatchDeleteImage` | Lifecycle service or manual user deleted images |
| `DeleteRepository` | Repository deleted (irreversible) |
| `SetRepositoryPolicy` | Resource-based policy changed |
| `PutImageTagMutability` | Tag mutability changed |
| `StartImageScan` | Scan-on-push or manual scan initiated |

Lifecycle-driven deletions appear as `BatchDeleteImage` events with
the ECR service principal (`ecr.amazonaws.com`) as the actor. Manual
deletions show the IAM user/role as the actor.

## Common managed policies

| Managed policy | Grants | Use case |
|---|---|---|
| `AmazonEC2ContainerRegistryReadOnly` | `ecr:GetAuthorizationToken`, `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`, `ecr:BatchCheckLayerAvailability`, plus `Describe*` / `List*` | Pull-only consumers, auditors |
| `AmazonEC2ContainerRegistryPowerUser` | All of ReadOnly plus `ecr:PutImage`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:BatchDeleteImage` | CI/CD push pipelines |
| `AmazonEC2ContainerRegistryFullAccess` | All ECR actions | Registry administrators |

For cross-account, attach the ReadOnly (pull) or PowerUser (push)
managed policy to the caller's IAM role AND add the matching
repository resource-based policy statement.
