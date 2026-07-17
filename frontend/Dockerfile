# syntax=docker/dockerfile:1

FROM node:22-alpine AS base
WORKDIR /app
RUN addgroup -S sentris && adduser -S sentris -G sentris
COPY package.json package-lock.json* ./
RUN npm install

# --- dev: fast refresh, source mounted as a volume ---
# Deliberately runs as root (unlike `prod`): docker-compose.yml layers
# anonymous volumes over /app/node_modules and /app/.next to protect them
# from the host bind mount, and those volumes are created root-owned by
# Docker. This stage never ships or gets scanned — only `prod` does.
FROM base AS dev
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# --- build: produce the standalone production output ---
FROM base AS build
COPY . .
RUN npm run build

# --- prod: minimal runtime image, non-root ---
FROM node:22-alpine AS prod
WORKDIR /app
RUN addgroup -S sentris && adduser -S sentris -G sentris
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
USER sentris
EXPOSE 3000
CMD ["node", "server.js"]
