# Frontend image: built with Node, served by Caddy (which also proxies /api to the backend).
# Build context: the repository root. The official node:22 images have no s390x build, so the
# build stage uses Red Hat's UBI Node.js 22 image (glibc, which rollup's s390x binary needs).
FROM registry.access.redhat.com/ubi10/nodejs-22 AS build
WORKDIR /opt/app-root/src
COPY --chown=1001:0 frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY --chown=1001:0 frontend/ ./
RUN npm run build

FROM caddy:2
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /opt/app-root/src/dist /srv
