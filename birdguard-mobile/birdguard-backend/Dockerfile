# Builds and runs all three BirdGuard NestJS services (api-gateway,
# auth-service, device-service) inside ONE container/machine, to fit
# within a 2-machine free tier alongside the existing craftelle app.
# They still talk to each other over TCP exactly as designed --
# localhost inside one container instead of three separate machines.

# --- Build stage: install deps (incl. devDeps) and compile each service ---
FROM node:20-alpine AS build

WORKDIR /app

COPY api-gateway/package*.json ./api-gateway/
COPY auth-service/package*.json ./auth-service/
COPY device-service/package*.json ./device-service/

RUN cd api-gateway && npm ci
RUN cd auth-service && npm ci
RUN cd device-service && npm ci

COPY api-gateway ./api-gateway
COPY auth-service ./auth-service
COPY device-service ./device-service

RUN cd api-gateway && npm run build && npm prune --omit=dev
RUN cd auth-service && npm run build && npm prune --omit=dev
RUN cd device-service && npm run build && npm prune --omit=dev

# --- Runtime stage: only compiled output + production node_modules ---
FROM node:20-alpine AS runtime

# Tailscale runs as a sidecar so device-service can reach the Pi over a
# private mesh network instead of needing a public route to its LAN IP.
RUN apk add --no-cache bash tailscale iptables ip6tables

WORKDIR /app

COPY --from=build /app/api-gateway/node_modules ./api-gateway/node_modules
COPY --from=build /app/api-gateway/dist ./api-gateway/dist
COPY --from=build /app/api-gateway/package.json ./api-gateway/package.json

COPY --from=build /app/auth-service/node_modules ./auth-service/node_modules
COPY --from=build /app/auth-service/dist ./auth-service/dist
COPY --from=build /app/auth-service/package.json ./auth-service/package.json

COPY --from=build /app/device-service/node_modules ./device-service/node_modules
COPY --from=build /app/device-service/dist ./device-service/dist
COPY --from=build /app/device-service/package.json ./device-service/package.json

COPY start.sh ./start.sh
RUN chmod +x ./start.sh

ENV HTTP_PORT=3000 \
    AUTH_SERVICE_HOST=127.0.0.1 \
    AUTH_SERVICE_PORT=3001 \
    DEVICE_SERVICE_HOST=127.0.0.1 \
    DEVICE_SERVICE_PORT=3002

EXPOSE 3000

CMD ["./start.sh"]
