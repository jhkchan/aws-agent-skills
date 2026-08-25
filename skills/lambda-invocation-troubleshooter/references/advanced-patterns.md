# Advanced Patterns — Lambda Invocation Troubleshooter

Deep-dive material moved verbatim from SKILL.md: quick-start rules,
mindset, philosophy, Step-0 non-obvious behaviours, and recent AWS
features. Load on demand.

### Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  TaskTimeoutException → TIMEOUT_CONFIG / TIMEOUT_DOWNSTREAM / VPC_CONNECTIVITY;
  Runtime.ExitError / OOM → MEMORY_CONFIG; high p99 init duration on first
  invocation → COLD_START; AccessDenied → PERMISSION_EXECUTION_ROLE /
  PERMISSION_RESOURCE_POLICY; function cannot reach internet / AWS service →
  VPC_CONNECTIVITY / VPC_ENDPOINT; "Could not decrypt KMS" / decrypt error →
  ENV_VAR_KMS; "variable is not defined" → ENV_VAR_MISSING; async retries
  forever / DLQ fills → INVOCATION_ASYNC; sync caller times out →
  INVOCATION_SYNC; ECR image pull / ImagePullFailure → ECR_IMAGE / ECR_POLICY.
- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A ROOT_CAUSE_FOUND verdict requires
  positive evidence — a failing probe that matches the symptom — not a
  process of elimination that "must be the timeout."
- **Memory on Lambda is not just RAM — it is also CPU.** Lambda allocates
  CPU proportional to memory (linear up to 6 vCPUs at 10 GB). A function
  that times out at 128 MB often succeeds at 512 MB with no code change,
  because the CPU proportion doubles and the bottlenecked compute-bound
  step runs faster. Always cross-check Duration against MemorySize before
  recommending a higher timeout.
- **Sync (RequestResponse) and async (Event) invocations fail in very
  different ways.** Sync fails with whatever the function throws back to
  the caller (timeout, 502, error payload). Async retries twice (by
  default), routes failures to a DLQ or OnFailure destination, and never
  surfaces the error to the caller. Operators debugging async with sync
  tooling miss the retry storm entirely.
- **ESCALATE for AWS-side incidents.** A regional Lambda or ECR outage,
  KMS key inaccessible because the key material was deleted, or a service
  event in AWS Health is not customer-fixable — escalate to AWS Support
  and surface the event ARN.

### Mindset

A failing Lambda invocation is usually a configuration or runtime
environment incident wearing a code costume. The handler is fine in the
majority of cases; the broken thing is timeout, memory, role, network
egress, environment decryption, invocation semantics, or image
distribution. Treat the function code as innocent until the config, role,
network, and runtime layers are proven clean. Senior serverless engineers
do not start by reading the handler; they start with
`get-function-configuration` and the most recent log stream, and only
open the handler once config and runtime are confirmed correct.

### Philosophy


Four behaviours separate a senior Lambda engineer from a generalist:

- **The error type drives the diagnostic order.** A `TaskTimeoutException`
  tells you the function was killed by the Lambda service at the configured
  timeout — that is a config or downstream-latency problem, not a code
  bug. An `Runtime.ExitError` with `ErrorType:OutOfMemory` tells you the
  runtime container exceeded its memory allocation — that is a memory
  sizing problem. A `ResourceNotFoundException` from the SDK inside the
  logs tells you the function code ran but the downstream resource was
  unreachable — that is a permissions or network problem. Routing the
  symptom to the wrong layer is the #1 source of wasted cycles in
  Lambda incidents.
- **Lambda VPC connectivity is the inverse of EC2 VPC connectivity.** An
  EC2 instance in a public subnet reaches the internet via the IGW. A
  Lambda function in a public subnet has NO internet access — there is no
  ENA for the function in a public subnet to bind to a public IP. A
  Lambda function reaches the internet ONLY when placed in a private
  subnet with a route to a NAT Gateway. Operators who "just put the
  function in the default VPC" often discover the function cannot reach
  external APIs because the default VPC is public. Always check the
  subnet route table for a NAT route when the symptom is "function
  cannot reach the internet."
- **Cold start is a per-environment, not a per-function, phenomenon.**
  Each unique (code + configuration + execution environment) tuple has
  its own warm pool. A function with two alias versions (PROD, STAGE)
  has two warm pools. SnapStart (Java only) pre-initialises the runtime
  against a snapshot; provisioned concurrency pre-Initialises N execution
  environments. A function with provisioned concurrency on one alias but
  not another shows cold starts only on the un-provisioned alias.
  Operators measuring "the function has a 3s cold start" without
  qualifying which alias, version, and traffic class see noisy
  measurements and chase ghosts.
- **Async retries are silent and exponential.** Lambda async invokes
  (Event invocation type) retry twice after the first failure: immediate,
  then +1 minute, then +2 minutes (default). The caller has already
  received a 202 and moved on — the retries happen entirely server-side.
  Without a DLQ or OnFailure destination configured, the failed events
  vanish. Operators who "don't see the retries" are looking at the caller
  logs; they need to look at the function's own `Errors` metric and the
  throttling / DLQ metrics.

### Step 0: Non-obvious behaviours that change diagnosis


These are the operational gotchas a senior Lambda engineer knows from
incident experience. Each one routes a diagnosis away from the obvious
layer to a less obvious one:

- **Lambda CPU scales with memory, linearly.** At 128 MB the function
  receives ~0.083 vCPU; at 1,769 MB it receives 1 full vCPU; at 10,240 MB
  it receives 6 vCPUs. A compute-bound function (JSON parsing, crypto,
  image processing) that times out at 256 MB frequently succeeds at 1 GB
  with NO code change — the CPU proportion quadrupled and the
  bottlenecked step ran in a quarter of the time. Operators who "raise
  the timeout" instead of the memory are paying for longer wall-clock
  execution without addressing the bottleneck.

- **`TaskTimeoutException` is emitted by the Lambda service, not the
  function.** The service sends SIGKILL to the container at the configured
  timeout; the function gets no chance to clean up. The last log line
  before the kill is the best evidence of where time was spent. A timeout
  with no preceding log line means the cold-start init itself exceeded
  the timeout — a Java function with a 5-second timeout and a 7-second
  init fails on every cold start with `TaskTimeoutException` and zero
  application logs.

- **Cold-start init duration is NOT application latency.** A function
  with `InitDuration: 4500 ms` and `Duration: 50 ms` has a 50 ms
  application cost; the 4500 ms is one-time per execution environment.
  Operators who add the two together and report "the function takes 4.5
  seconds" overstate p99 latency by orders of magnitude. Always read
  `InitDuration` and `Duration` as separate metrics.

- **SnapStart is Java-only and requires a code-deploy cycle to enable.**
  SnapStart takes a memory snapshot of the initialised runtime and
  restores it for each new execution environment, reducing init duration
  from seconds to milliseconds. It is only available for Java 11+ on
  supported managed runtimes. Python and Node do not benefit (their init
  is already fast). Operators enabling SnapStart on a Node function see
  zero benefit and assume SnapStart is broken.

- **Provisioned concurrency costs money per-second regardless of
  invocations.** It pre-initialises N execution environments and bills
  them as `ProvisionedConcurrencySpilloverInvocations` once traffic
  exceeds N. It is the right tool for cold-start-sensitive workloads
  (sync API-facing functions); it is the wrong tool for async batch
  processing where a 2-second cold start is acceptable.

- **Cross-account Lambda invocation requires BOTH the caller's
  identity-based `lambda:InvokeFunction` AND the function's
  resource-based policy listing the caller.** Same-account requires only
  one. Operators who "added the IAM permission to the caller" but still
  see AccessDenied from a cross-account caller miss the resource-based
  policy side.

- **A Lambda function in a VPC has NO internet access unless a NAT
  Gateway exists in the route table.** This is the inverse of EC2 and
  surprises every operator the first time. The function in a public
  subnet also has no internet — public subnets route to the IGW, but
  Lambda functions do not get a public IP, so traffic to the IGW has
  no return path. Always place Lambda in a private subnet when VPC
  attachment is needed.

- **VPC-attached Lambda functions reach AWS services (S3, DynamoDB,
  SQS, etc.) over the public service endpoint by default — which means
  they need a NAT Gateway to reach them.** The cheaper, more secure
  alternative is a VPC endpoint (Gateway or Interface) for the service.
  A function that can reach DynamoDB but not S3 is a classic pattern:
  DynamoDB has a Gateway endpoint (free, automatic), S3 also does, but
  many other services require an Interface endpoint (hourly charge).

- **KMS-encrypted environment variables require `kms:Decrypt` on the
  execution role for the CUSTOMER MANAGED key only.** If the function
  uses the default Lambda service key (`aws/lambda`), no `kms:Decrypt`
  permission is required — Lambda decrypts transparently. Operators who
  add `kms:Decrypt` permissions for the service-managed key are chasing
  a non-issue; operators who rotate to a customer-managed key without
  adding `kms:Decrypt` to the role break every invocation.

- **Container-image Lambda functions pull the image at init time, not at
  invocation time.** A 5 GB image takes 30-60 seconds to pull on a cold
  start, dwarfing the application's compute time. Image pull happens
  once per execution environment lifecycle; warm invocations do not
  re-pull. Operators who report "function is slow" with a large image
  are paying the pull cost on every cold start.

- **`PackageType: Image` functions have a 10 GB compressed image size
  cap.** Above the cap, the function cannot be created or updated. The
  practical performance ceiling is much lower — images above 500 MB
  introduce visible init latency on every cold start.

- **Event-source mapping (SQS, Kafka, DynamoDB Streams, Kinesis) has
  its own retry semantics that differ from async invokes.** A failed
  batch is retried in full up to `MaximumRetryAttempts`; on exhaustion,
  the partial-item failure is sent to an `OnFailure` destination
  (if configured) or discarded. `BisectBatchOnFunctionError` and
  `MaximumBatchingWindowInSeconds` further shape the retry behaviour.
  Operators who debug event-source failures as if they were async
  retries miss the batch-level semantics.

- **Lambda Layers are versioned and immutable, but a function references
  a specific Layer version by ARN.** Deleting a Layer version does not
  affect existing functions that reference it, but a function update
  that re-resolves the ARN fails if the version was deleted. Operators
  who "deleted the old Layer to clean up" break the next deploy.

### Recent AWS features (2024-2026)


- **SnapStart for Java 21 and above (2024-2025):** Extended runtime
  support; restore-from-snapshot now covers more JVM frameworks.
  Diagnostically, SnapStart must be enabled on a function BEFORE
  publishing a version; existing versions cannot retroactively benefit.
- **Provisioned concurrency pricing simplification (2024):** Flat
  per-hour pricing by memory size; spillover to on-demand priced
  separately. Diagnostically, `ProvisionedConcurrentExecutions` metric
  should be the steady-state target; sustained spillover indicates
  under-provisioning.
- **Lambda container image 10 GB cap (2024):** Raised from 3 GB; large
  ML inference and game-server-style workloads can fit. Cold-start
  cost scales with image size; always audit size before recommending
  container functions.
- **BisectBatchOnFunctionError default-on for SQS (2024-2025):** New
  event source mappings default to bisect-on-error, accelerating the
  isolation of poison-pill records. Older mappings may still have it
  disabled.
- **Lambda runtime deprecation schedule (2024-2025):** Node 16, Python
  3.7, Java 8 (older variants) decommissioned. Functions on these
  runtimes continue to execute but block updates; AWS forces
  decommission on the published date. Plan runtime upgrades before
  the deprecation date.
- **Lambda Response Streaming (2024-2025):** Functions can stream
  responses via Function URL; changes how "first byte" latency is
  measured. Init duration still applies; first-byte latency is
  separate from end-to-end Duration.
