# .ebextensions and Platforms — Elastic Beanstalk Deployer

Deep reference on .ebextensions configuration (option_settings,
Resources, files, commands, container_commands), .platform hooks on
Amazon Linux 2023, platform branches and solution stacks, and platform
deprecation timelines. Loaded on demand by the skill — kept out of
the main SKILL.md body so the provisioning procedure stays scannable.

## .ebextensions fundamentals

### Directory structure

`.ebextensions/` lives at the root of the source bundle. Files are
processed in lexicographic order — prefix with `NN-` to enforce
ordering.

```text
app.zip
├── .ebextensions/
│   ├── 01-options.config
│   ├── 02-rds.config
│   └── 03-hooks.config
├── .platform/
│   └── hooks/
│       ├── prebuild/
│       │   └── 01-install-deps.sh
│       ├── predeploy/
│       │   └── 01-create-dirs.sh
│       └── postdeploy/
│           └── 01-warmup.sh
├── package.json
└── server.js
```

### .config file sections

Each `.config` file supports these top-level keys:

| Key | When it runs | Purpose |
|---|---|---|
| `option_settings` | During environment configuration | Beanstalk namespace options |
| `Resources` | During CloudFormation stack creation | Create/modify AWS resources |
| `files` | Before app deployment | Write files to EC2 instances |
| `commands` | Before app deployment | Run shell commands (as root) |
| `container_commands` | During app deployment | Run commands in the app directory |
| `services` | After commands | Manage sysvinit services |

### option_settings example

```yaml
option_settings:
  - namespace: aws:elasticbeanstalk:application:environment
    option_name: NODE_ENV
    value: production
  - namespace: aws:elasticbeanstalk:container:nodejs
    option_name: NodeCommand
    value: "npm start"
  - namespace: aws:elasticbeanstalk:managedactions
    option_name: ManagedActionsEnabled
    value: true
```

### Resources example (RDS with Retain)

```yaml
Resources:
  AWSEBRDSDatabase:
    Type: AWS::RDS::DBInstance
    Properties:
      AllocatedStorage: 20
      DBInstanceClass: db.t3.micro
      Engine: postgres
      EngineVersion: "15"
      MasterUsername: myapp
      MasterUserPassword: !Ref DBPassword
      DeletionPolicy: Retain
      DBSubnetGroupName: !Ref MyDBSubnetGroup
```

**Critical:** `DeletionPolicy: Retain` ensures the RDS instance
survives environment termination. Without it, terminating the
environment destroys the database.

### container_commands example

```yaml
container_commands:
  01_migrate:
    command: "npm run migrate"
    leader_only: true
  02_seed:
    command: "npm run seed"
    leader_only: true
  03_clear_cache:
    command: "npm run cache:clear"
```

`leader_only: true` runs the command on ONLY ONE instance in the ASG.
This is critical for database migrations — you don't want multiple
instances running migrations simultaneously.

## .platform hooks (Amazon Linux 2023)

On AL2023, `.platform/hooks/` replaces `.ebextensions/hooks/`. Hooks
are executable scripts organized by deployment phase:

| Phase | When it runs | Use case |
|---|---|---|
| `prebuild/` | Before the application build step | Install dependencies |
| `predeploy/` | Before the application is deployed to the server | Create directories, set permissions |
| `postdeploy/` | After the application is deployed and the server is started | Warmup, smoke tests |

Scripts must be executable (`chmod +x`) and have a shebang line.

```bash
# .platform/hooks/postdeploy/01-warmup.sh
#!/bin/bash
curl -s http://localhost:3000/health || exit 1
```

## Platform branches and solution stacks

### Amazon Linux 2023 (AL2023)

AL2023 is the current generation Beanstalk platform. Key improvements
over AL2:

- Deterministic package updates via DNF (not YUM)
- Faster boot times
- Smaller AMI footprint
- Improved security posture
- `.platform/hooks/` support (replaces `.ebextensions/hooks/`)

### Available AL2023 solution stacks

```bash
# List all available solution stacks
aws elasticbeanstalk list-available-solution-stacks \
  --query 'SolutionStacks[?contains(@, `Amazon Linux 2023`)]' \
  --output table
```

### Platform lifecycle

Each platform branch has a lifecycle:

1. **Beta:** new platform version, may have breaking changes.
2. **Supported:** production-ready, receives managed updates.
3. **Deprecated:** no new minor versions; existing versions still work
   but should migrate.
4. **Retired:** platform is no longer available. Environments must
   migrate to a supported branch.

**Amazon Linux 2 (AL2)** platform branches are in deprecation. All
new environments MUST use AL2023.

### Graviton (arm64) support

AL2023 platforms support Graviton-based instances for cost-optimized
compute. Specify `arm64` in the solution stack:

```text
64bit Amazon Linux 2023 v6.0.4 running Node.js 20 (arm64)
```

Graviton instances (e.g., `t4g.medium`, `c7g.large`) offer up to 20%
price/performance improvement over equivalent x86 instances.

## Common .ebextensions pitfalls

1. **Malformed YAML:** a syntax error in any `.config` file causes the
   ENTIRE deployment to fail. Validate YAML before deploying.

2. **Wrong ordering:** a resource referenced in `01-config.config` but
   created in `02-config.config` fails. Use lexicographic prefixing.

3. **Missing DeletionPolicy:** attached RDS, DynamoDB tables, or S3
   buckets created in .ebextensions are terminated WITH the environment.
   Set `DeletionPolicy: Retain` for resources that must persist.

4. **container_commands cwd:** `container_commands` run in the
   application directory (not the system root). Use relative paths or
   `$APP_DIR`.

5. **Platform incompatibility:** `.ebextensions/hooks/` is NOT
   supported on AL2023. Use `.platform/hooks/` instead.

## Step 11 .ebextensions config examples (from SKILL.md)

**`.ebextensions/01-options.config`** — set namespace options and
environment variables:
```yaml
option_settings:
  - namespace: aws:elasticbeanstalk:application:environment
    option_name: NODE_ENV
    value: production
```

**`.ebextensions/02-rds.config`** — create an RDS instance:
```yaml
Resources:
  AWSEBRDSDatabase:
    Type: AWS::RDS::DBInstance
    Properties:
      AllocatedStorage: 20
      DBInstanceClass: db.t3.micro
      Engine: postgres
      MasterUsername: myapp
      DeletionPolicy: Retain
```

**`.ebextensions/03-hooks.config`** — deployment hooks:
```yaml
container_commands:
  01_migrate:
    command: "npm run migrate"
    leader_only: true
```
