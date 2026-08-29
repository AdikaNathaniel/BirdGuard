# api-gateway

BirdGuard's HTTP REST entry point. Plain NestJS HTTP app on port `3000` that validates requests,
forwards them to `auth-service` and `device-service` over TCP (`@nestjs/microservices`
`ClientProxy`), and translates their responses into proper HTTP status codes. This is the only
service the Flutter app talks to directly.

## Setup

```bash
npm install
cp .env.example .env   # adjust JWT_SECRET etc.; must match auth-service's JWT_SECRET
npm run start:dev
```

Requires `auth-service` (port 3001) and `device-service` (port 3002) to be running for requests to
succeed - see the root `birdguard-backend/README.md`.

## Environment variables

See `.env.example`:

| Variable               | Default     | Notes                                    |
|--------------------------|--------------|---------------------------------------------|
| `HTTP_PORT`             | `3000`      | HTTP port Flutter/clients connect to        |
| `AUTH_SERVICE_HOST`     | `127.0.0.1` | auth-service TCP host                       |
| `AUTH_SERVICE_PORT`     | `3001`      | auth-service TCP port                       |
| `DEVICE_SERVICE_HOST`   | `127.0.0.1` | device-service TCP host                     |
| `DEVICE_SERVICE_PORT`   | `3002`      | device-service TCP port                     |
| `JWT_SECRET`            | dev placeholder | **Must match** `auth-service`'s JWT secret |

## Routes

- `POST /auth/register` - public. Body: `{ email, username, password, userType? }`. Returns `201`
  with the created user, or `409` if email/username taken.
- `POST /auth/login` - public. Body: `{ email, password }`. Returns `200` with
  `{ accessToken }`, or `401` on bad credentials.
- `POST /device/detector/start` - **requires** `Authorization: Bearer <accessToken>`. Starts the
  person detector on the Pi.
- `POST /device/detector/stop` - **requires** JWT. Stops the person detector on the Pi.
- `GET /device/detector/status` - **requires** JWT. Returns `{ success, running, pid? }`.

All `/device/*` routes are protected by `JwtAuthGuard`, verifying the JWT against the same
`JWT_SECRET` as `auth-service`.
