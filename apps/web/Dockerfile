# Production image for the Next.js web app (standalone output).
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* values are baked in at build time.
ARG NEXT_PUBLIC_ENABLE_GRANULAR_WORKFLOW=true
ENV NEXT_PUBLIC_ENABLE_GRANULAR_WORKFLOW=$NEXT_PUBLIC_ENABLE_GRANULAR_WORKFLOW
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# The rewrite target for /api/v1 (server-side proxy to the API container).
ENV API_BASE_URL=http://api:8000
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
