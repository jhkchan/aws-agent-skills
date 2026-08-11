# Amplify Gen 2 Backend Reference

Deep reference on Amplify Gen 2 (TypeScript CDK-based) backend patterns:
`defineBackend` in `amplify/backend.ts`, auth (Cognito), data (AppSync
GraphQL), storage (S3), functions (Lambda), CI deployment via
`ampx pipeline-deploy`, branch-based backend stacks, and integration
with the frontend build. Loaded on demand by the skill.

## Gen 2 vs Gen 1

| Aspect | Gen 1 (legacy) | Gen 2 (current) |
|---|---|---|
| Backend definition | `amplify init` + `amplify add auth/data/...` CLI mutations | `amplify/backend.ts` with `defineBackend` (TypeScript) |
| IaC | Generated CloudFormation; mutation model | CDK constructs (fully typed) |
| Deploy | `amplify push` | `npx ampx pipeline-deploy` (CI) or `npx ampx sandbox` (dev) |
| Branching | Single backend, env var per env | Per-branch backend stack (Cognito, AppSync, S3 per branch) |
| Composition | Limited | Any CDK construct |
| Status | Maintenance; no new features | Active development (2024-2026) |

New apps should use Gen 2. Gen 1 migrations are documented in the
AWS Amplify migration guide.

## defineBackend skeleton

```typescript
// amplify/backend.ts
import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';
import { storage } from './storage/resource';
import { myFunction } from './functions/my-function/resource';

export const backend = defineBackend({
  auth,
  data,
  storage,
});

// Wire the function to the API as a resolver
backend.data.resources.cfnResources.cfnGraphQLApi.addDependency(
  backend.myFunction.resources.cfnFunction
);
```

## Auth (Cognito)

```typescript
// amplify/auth/resource.ts
import { defineAuth } from '@aws-amplify/backend';

export const auth = defineAuth({
  name: 'myAuth',
  loginWith: {
    email: true,
    // social providers
    externalProviders: {
      google: {
        clientId: process.env.GOOGLE_CLIENT_ID!,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
        scopes: ['email', 'profile'],
      },
    },
  },
  multifactor: {
    mode: 'OPTIONAL',
    sms: true,
  },
});
```

Frontend usage:

```typescript
import { signIn, signOut, getCurrentUser } from 'aws-amplify/auth';
await signIn({ username, password });
const user = await getCurrentUser();
```

## Data (AppSync GraphQL)

```typescript
// amplify/data/resource.ts
import { type ClientSchema, a, defineData } from '@aws-amplify/backend';

const schema = a.schema({
  Todo: a
    .model({
      content: a.string(),
      done: a.boolean(),
    })
    .authorization(allow => [allow.owner()]),

  Echo: a
    .query()
    .arguments({ message: a.string().required() })
    .returns(a.string().required())
    .handler(a.handler.function('my-function'))
    .authorization(allow => [allow.publicApiKey()]),
});

export type Schema = ClientSchema<typeof schema>;

export const data = defineData({
  schema,
  authorizationModes: {
    defaultAuthorizationMode: 'userPool',
  },
});
```

Frontend usage:

```typescript
import { generateClient } from 'aws-amplify/data';
import type { Schema } from '../amplify/data/resource';
const client = generateClient<Schema>();
const { data: todos } = await client.models.Todo.list();
```

## Storage (S3)

```typescript
// amplify/storage/resource.ts
import { defineStorage } from '@aws-amplify/backend';

export const storage = defineStorage({
  name: 'myStorage',
  access: (allow) => ({
    'media/*': [
      allow.authenticated.to(['read', 'write']),
      allow.guest.to(['read']),
    ],
    'private/{entity_id}/*': [
      allow.entity('identity').to(['read', 'write', 'delete']),
    ],
  }),
});
```

## Functions (Lambda)

```typescript
// amplify/functions/my-function/resource.ts
import { defineFunction } from '@aws-amplify/backend';

export const myFunction = defineFunction({
  name: 'myFunction',
  entry: './handler.ts',
});
```

```typescript
// amplify/functions/my-function/handler.ts
import type { EventHandler } from '@aws-amplify/backend';
export const handler: EventHandler = async (event) => {
  return { message: `Echo: ${event.arguments.message}` };
};
```

## CI deployment (pipeline-deploy)

The backend deploy runs in the `amplify.yml` build phase:

```yaml
build:
  commands:
    - npx ampx pipeline-deploy --branch $AWS_BRANCH --app-id $AWS_APP_ID
```

This reads the branch name and deploys a branch-specific backend stack:

- `main` → stack `amplify-prodweb-main-...`
- `staging` → stack `amplify-prodweb-staging-...`
- `pr123` → stack `amplify-prodweb-pr123-...`

Each branch's Cognito user pool, AppSync API, and S3 bucket are
independent — a bug in `staging` cannot affect `main`.

### Prerequisites for pipeline-deploy

1. **CDK bootstrap** in the account + region:
   ```bash
   npx cdk bootstrap aws://<account>/<region>
   ```
2. **Amplify service role** with `iam:PassRole` and CDK permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["iam:PassRole", "cloudformation:*", "sts:AssumeRole"],
       "Resource": "*"
     }]
   }
   ```
3. **AWS App ID env var** (`$AWS_APP_ID`) — set automatically by
   Amplify during the build.

## Local sandbox (dev only)

For local development with hot reload:

```bash
npx ampx sandbox
```

This deploys a personal backend stack (named `sandbox`) that mirrors
the local `amplify/backend.ts`. NEVER run `ampx sandbox` in CI — it
creates an orphan stack. CI uses `pipeline-deploy`.

## Connecting frontend to backend

Amplify Gen 2 generates `amplify_outputs.json` (config) at deploy time.
The frontend reads it via:

```typescript
// src/main.ts (or app entrypoint)
import { Amplify } from 'aws-amplify';
import outputs from '../amplify_outputs.json';
Amplify.configure(outputs);
```

For `pipeline-deploy` builds, `amplify_outputs.json` is generated in
the project root during the build phase — commit a placeholder or
.gitignore it; Amplify regenerates it on every build.
