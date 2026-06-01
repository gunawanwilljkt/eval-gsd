# Talk — minimal 1:1 WebRTC signaling server.
# Signaling-only (the server never sees media): HTTP static + /healthz + /ice-servers,
# and a WebSocket relay on /ws. TURN + TLS are supplied at runtime via env (see docs/DEPLOY.md).

FROM node:22-alpine

WORKDIR /app

# Install only the server's runtime dependency (ws). Copy manifests first for layer caching.
COPY server/package.json server/package-lock.json* ./server/
RUN cd server && npm install --omit=dev

# App code: the server and the static client it serves.
COPY server/ ./server/
COPY public/ ./public/

# The signaling port (override with -e PORT=...). When TLS_CERT_FILE/TLS_KEY_FILE are mounted
# and set, the same port serves HTTPS + wss instead of HTTP + ws.
ENV PORT=8080
EXPOSE 8080

WORKDIR /app/server
CMD ["node", "server.js"]
