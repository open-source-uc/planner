FROM node:16-alpine

WORKDIR /app

# Install curl for healthcheck
RUN apk --no-cache add curl

EXPOSE 3004
COPY ./data/cas-mock-users.json.example /app/data/cas-mock-users.json

HEALTHCHECK CMD curl --fail http://localhost:3004/ || exit 1

CMD ["npx", "--yes", "cas-server-mock", "--port=3004", "--database=/app/data/cas-mock-users.json"]
