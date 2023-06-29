# ========= BUILD =========
FROM node:16-alpine as builder

# Set the working directory
WORKDIR /tmp

# Copy package.json and package-lock.json to the working directory
COPY package*.json .

# Install production dependencies
RUN npm ci --only=prod

# Create `.env` from `.env.docker`
COPY ./.env.docker /tmp/.env

# Copy other files to the working directory
COPY . .

# Build the application
RUN npm run build

# ========= RUN =========
FROM caddy:2-alpine

# Copy the build folder from builder stage to the Caddy directory
COPY --from=builder /tmp/dist /srv

# Copy Caddyfile for configuration
COPY conf/Caddyfile /etc/caddy/Caddyfile

# RUN npm run preview
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
