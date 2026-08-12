# SC-TPCRS frontend -- PRODUCTION image (multi-stage: build with Node, serve
# with nginx). Contrast with Dockerfile.dev, which runs the Vite dev server.
# Build context is ./frontend (see docker-compose.yml `frontend-prod`).
#
#   docker build -f frontend/Dockerfile -t sctpcrs-frontend:prod \
#       --build-arg VITE_API_BASE_URL=/api ./frontend
#
# By default the SPA calls a SAME-ORIGIN "/api", which nginx reverse-proxies to
# the gateway (no CORS). For a cross-origin deploy instead, build with an
# absolute base (e.g. --build-arg VITE_API_BASE_URL=https://api.example.com/api)
# and point the browser straight at the gateway.

# ---- build stage ---------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app

# Vite inlines VITE_* at build time, so the API base is baked into the bundle.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Install deps from the lockfile first (layer caching), then build.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- runtime stage -------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# The host:port the /api/ location proxies to. Defaults to the compose gateway;
# override per environment, e.g. -e API_UPSTREAM=http://my-gateway:8000
ENV API_UPSTREAM=http://gateway:8000
# Substitute ONLY ${API_UPSTREAM} in the template; leave $uri/$host/etc. intact.
ENV NGINX_ENVSUBST_FILTER=API_UPSTREAM

# Rendered into /etc/nginx/conf.d/default.conf by the base image entrypoint.
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
# CMD (nginx -g 'daemon off;') and the envsubst entrypoint come from the base image.
