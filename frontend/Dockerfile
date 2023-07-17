# ========= BUILD CADDY =========
FROM caddy:2-builder-alpine AS caddy-builder
RUN xcaddy build \
    --with github.com/greenpau/caddy-security \
    --with github.com/greenpau/caddy-trace \
    --with github.com/abiosoft/caddy-exec

# ========= BUILD APP =========
FROM node:16-alpine as app-builder

# Set the working directory
WORKDIR /tmp

# Copy package.json and package-lock.json to the working directory
COPY package*.json .

# Install dependencies
RUN npm ci

# Copy other files to the working directory
COPY . .

# Build the application
RUN npm run build

# ========= RUN =========
FROM caddy:2-alpine

# Copy Caddy binary from its builder stage
COPY --from=caddy-builder /usr/bin/caddy /usr/bin/caddy

# Install curl for healthcheck
RUN apk --no-cache add curl

# Copy the build folder from the app builder stage to the Caddy directory
COPY --from=app-builder /tmp/dist /srv

# Copy Caddyfile for configuration
COPY conf/Caddyfile /etc/caddy/Caddyfile

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:80/ || exit 1

# Run caddy using config file
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]

