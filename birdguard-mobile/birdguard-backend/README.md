# birdguard-backend

NestJS microservices backend for BirdGuard. Lets the (future) BirdGuard mobile app register/log
in users and remotely control the Raspberry Pi's person detector over SSH, without ever exposing
Pi credentials or a raw shell to the client.

## Architecture

```
                 HTTP (REST)                 TCP (@nestjs/microservices)
Flutter app  ─────────────────►  api-gateway  ─────────────────►  auth-service    (SQLite/Prisma)
                                  (port 3000)  ─────────────────►  device-service  (SSH to the Pi)
                                               (auth-service: 3001, device-service: 3002)
```

- **api-gateway** (`api-gateway/`, port `3000`) - the only service the app talks to. Plain HTTP
  REST, validates input with DTOs + a global `ValidationPipe`, forwards requests to the other two
  services via TCP `ClientProxy`, and guards `/device/*` routes with a JWT check.
- **auth-service** (`auth-service/`, port `3001`) - TCP-only microservice. Registers/authenticates
  users against a local SQLite database (via Prisma) and issues JWTs.
- **device-service** (`device-service/`, port `3002`) - TCP-only microservice. Holds the Pi's SSH
  credentials and can execute only a fixed, hardcoded whitelist of commands (start/stop/status of
  the person detector) - it never runs a client-supplied command string.

None of `auth-service` or `device-service` expose an HTTP port; they're only reachable from
`api-gateway` over TCP on localhost. The Flutter app never talks to them directly and never sees
the Pi's SSH credentials.

## Running all three locally

Each service is an independent NestJS project with its own `package.json`. Open three terminals:

```bash
# Terminal 1
cd birdguard-backend/auth-service
npm install
npx prisma generate
npx prisma migrate dev --name init
npm run start:dev

# Terminal 2
cd birdguard-backend/device-service
npm install
npm run start:dev

# Terminal 3
cd birdguard-backend/api-gateway
npm install
npm run start:dev
```

Each service has its own `.env` (already populated with localhost dev defaults) and
`.env.example`. Before running for real:
- Set the same `JWT_SECRET` in `auth-service/.env` and `api-gateway/.env`.
- Set `PI_HOST` (defaults to `192.168.43.233`), `PI_USERNAME`, and either `PI_PRIVATE_KEY_PATH` or
  `PI_PASSWORD` in `device-service/.env`.

## REST API surface (via api-gateway, port 3000)

### `POST /auth/register`
Public. Creates a user.

```bash
curl -X POST http://localhost:3000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","username":"birdwatcher","password":"hunter22","userType":"CUSTOMER"}'
```
`201` with the created user (no password hash), or `409` if the email/username is taken.

### `POST /auth/login`
Public. Returns a JWT.

```bash
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"hunter22"}'
```
`200` with `{ "accessToken": "<jwt>" }`, or `401` on bad credentials.

### `POST /device/detector/start`
Requires `Authorization: Bearer <accessToken>`. SSHes into the Pi and starts the person detector.

```bash
curl -X POST http://localhost:3000/device/detector/start \
  -H "Authorization: Bearer <accessToken>"
```
`{ "success": true, "output": "<pid>" }` or `{ "success": false, "error": "..." }` (e.g. Pi
offline).

### `POST /device/detector/stop`
Requires JWT. Stops the person detector.

```bash
curl -X POST http://localhost:3000/device/detector/stop \
  -H "Authorization: Bearer <accessToken>"
```

### `GET /device/detector/status`
Requires JWT. Reports whether the detector process is running.

```bash
curl http://localhost:3000/device/detector/status \
  -H "Authorization: Bearer <accessToken>"
```
`{ "success": true, "running": true, "pid": "1234" }` or `{ "success": true, "running": false }`.

## Security model

- The Pi's SSH credentials live only in `device-service`'s environment variables - never sent to
  or stored in the client app.
- `device-service` exposes exactly three actions (`startDetector`, `stopDetector`,
  `getDetectorStatus`), each mapped to one hardcoded shell command in
  `device-service/src/device/commands.ts`. No endpoint anywhere in this backend accepts a
  free-text/arbitrary shell command from a client - that's a deliberate boundary, not an
  oversight. Adding new device actions later (laser on/off, servo step, etc.) means adding a new
  named entry to that registry, not opening up free-text execution.
- `/device/*` routes require a valid JWT, issued only by `auth-service` after a successful login.

## Adding a new whitelisted device action

See "Adding a new device action" in `device-service/README.md`.
