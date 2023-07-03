FROM node:16-alpine

WORKDIR /app

EXPOSE 3004

COPY ./data/cas-mock-users.json.example /app/data/cas-mock-users.json

CMD ["npx", "--yes", "cas-server-mock", "--port=3004", "--database=/app/data/cas-mock-users.json"]
