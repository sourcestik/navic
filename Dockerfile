FROM node:24-bookworm-slim AS web
WORKDIR /web
RUN npm install --global pnpm@11.25.0
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm run build

FROM debian:bookworm-slim AS cpp
RUN apt-get update && apt-get install -y --no-install-recommends g++ gzip libcurl4-openssl-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY backend/ backend/
COPY scripts/build.sh scripts/build.sh
RUN sh scripts/build.sh
COPY data/graph.ndjson.gz data/graph.ndjson.gz
RUN gzip -d data/graph.ndjson.gz

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 libcurl4 ca-certificates && rm -rf /var/lib/apt/lists/* && useradd --create-home --uid 10001 navic
WORKDIR /app
COPY --from=cpp /src/build/navic-api /app/navic-api
COPY --from=cpp /src/data/graph.ndjson /app/data/graph.ndjson
COPY data/network.geojson data/metadata.json /app/data/
COPY docs/openapi.json docs/swagger.html /app/docs/
COPY --from=web /web/dist/ /app/frontend/dist/
ENV PORT=8080 HOST=0.0.0.0
USER navic
EXPOSE 8080
ENTRYPOINT ["/app/navic-api"]
