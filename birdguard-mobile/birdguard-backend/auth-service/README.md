# auth-service

BirdGuard's authentication microservice. Exposes a NestJS **TCP microservice** (no HTTP surface of
its own) on port `3001` with two message patterns, `{ cmd: 'register' }` and `{ cmd: 'login' }`,
consumed by `api-gateway`. User records are stored in a local SQLite file via Prisma.

## Setup

```bash
npm install
cp .env.example .env   # adjust JWT_SECRET etc. if needed; .env already has dev defaults
npx prisma generate
npx prisma migrate dev --name init
npm run start:dev
```

The first `prisma migrate dev` creates `prisma/dev.db` (SQLite file) and the `User` table.

## Environment variables

See `.env.example`:

| Variable              | Default                     | Notes                                          |
|------------------------|------------------------------|-------------------------------------------------|
| `AUTH_SERVICE_HOST`    | `127.0.0.1`                 | TCP bind host                                   |
| `AUTH_SERVICE_PORT`    | `3001`                      | TCP bind port                                   |
| `DATABASE_URL`         | `file:./dev.db`             | SQLite datasource for Prisma                    |
| `JWT_SECRET`           | dev placeholder             | **Must match** `api-gateway`'s JWT secret       |
| `JWT_EXPIRES_IN`       | `7d`                        | Access token lifetime                           |
| `BCRYPT_SALT_ROUNDS`   | `10`                        | bcrypt cost factor for password hashing         |

## Message patterns

### `{ cmd: 'register' }`

Payload: `{ email, username, password, userType? }` (`userType` one of `ADMIN`, `CUSTOMER`,
`SELLER`, `ANALYST`; defaults to `CUSTOMER`).

- Success: the created user object, without `passwordHash`.
- Failure: `{ statusCode: 409, message: 'Email already registered' }` (or `'Username already
  taken'`) if the email/username is already in use.

### `{ cmd: 'login' }`

Payload: `{ email, password }`.

- Success: `{ accessToken: '<jwt>' }`.
- Failure: `{ statusCode: 401, message: 'Invalid credentials' }`.

## Data model

`User` (see `prisma/schema.prisma`): `id` (uuid), `email` (unique), `username` (unique),
`passwordHash`, `userType` (string, constrained to the `UserType` enum in
`src/auth/user-type.enum.ts` — SQLite has no native enum column type so Prisma's SQLite connector
does not support `enum` in the schema; the constraint is enforced at the application layer via
`class-validator`), `createdAt`.
