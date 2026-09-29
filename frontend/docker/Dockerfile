# Used to build the image in GitLab CI/CD
FROM node:24.14.1-bookworm-slim AS builder

ENV CI=1

WORKDIR /build

# Base path the browser uses for API calls. Default is same-origin /api, which
# Cloudflare tunnels route to the backend (cloudflared keeps the /api prefix, and
# the FastAPI router is mounted at /api/names). For a separate API hostname,
# pass e.g. --build-arg VITE_API_BASE=https://api.example.com/api
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine

# Serve the SPA and proxy /api to the FastAPI backend — the "trivia fallback":
# the frontend forwards API calls itself, so requests reach the backend even if
# the Cloudflare tunnel's /api path rule doesn't route them there directly.
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 8080