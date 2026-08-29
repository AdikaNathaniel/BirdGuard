# device-service

BirdGuard's device-control microservice. Exposes a NestJS **TCP microservice** on port `3002` that
holds the Raspberry Pi's SSH credentials and can execute only a **fixed, whitelisted set of shell
commands** on the Pi (see `src/device/commands.ts`). It never accepts a free-text command from a
client - the client can only select one of `startDetector` / `stopDetector` / `getDetectorStatus`.

Each request connects to the Pi fresh over SSH, runs the one whitelisted command, and disconnects
- there's no persistent SSH session held across requests.

## Setup

```bash
npm install
cp .env.example .env   # fill in PI_PASSWORD or PI_PRIVATE_KEY_PATH
npm run start:dev
```

## Environment variables

See `.env.example`:

| Variable                | Default          | Notes                                                        |
|--------------------------|-------------------|----------------------------------------------------------------|
| `DEVICE_SERVICE_HOST`    | `127.0.0.1`      | TCP bind host                                                  |
| `DEVICE_SERVICE_PORT`    | `3002`           | TCP bind port                                                  |
| `PI_HOST`                | `192.168.43.233` | Raspberry Pi's LAN IP                                          |
| `PI_USERNAME`            | `pi`             | SSH username                                                   |
| `PI_PASSWORD`            | (empty)          | SSH password auth (used only if `PI_PRIVATE_KEY_PATH` unset)   |
| `PI_PRIVATE_KEY_PATH`    | (empty)          | Path to an SSH private key; takes priority over password auth  |
| `PI_SSH_TIMEOUT_MS`      | `10000`          | SSH connect timeout                                            |

## Message patterns

All three return a JSON object, never throw for expected failure modes (e.g. the Pi being
offline) - connection errors are caught and reported as `{ success: false, error: ... }`.

### `{ cmd: 'startDetector' }`
Runs `COMMANDS.START_DETECTOR`. Returns `{ success: true, output }` or `{ success: false, error }`.

### `{ cmd: 'stopDetector' }`
Runs `COMMANDS.STOP_DETECTOR`. Returns `{ success: true, output }` or `{ success: false, error }`.

### `{ cmd: 'getDetectorStatus' }`
Runs `COMMANDS.DETECTOR_STATUS` (a `pgrep`) and interprets the output. Returns
`{ success: true, running: boolean, pid?: string }` or `{ success: false, error }`.

## Adding a new device action

1. Add a new entry to `COMMANDS` in `src/device/commands.ts` - a fixed shell command string, no
   interpolation of client input.
2. Add a method on `DeviceService` that calls the private `runCommand()` helper with that key.
3. Add a `@MessagePattern({ cmd: '...' })` handler on `DeviceController`.
4. Add a matching route on `api-gateway`.

Never add an endpoint that accepts a raw/free-text command from the client - this whitelist is a
deliberate security boundary.
